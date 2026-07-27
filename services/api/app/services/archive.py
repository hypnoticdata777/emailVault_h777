from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from services.api.app.auth.identity import GoogleIdentity
from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import (
    ApiError,
    ArchivePreferences,
    ArchiveRecordReference,
    ArchiveResult,
    ArchiveState,
    ArchiveStatus,
    ErrorCategory,
    GmailFinalizationInstructions,
    VerificationSummary,
)
from services.api.app.domain.contracts import ArchiveThreadRequest
from services.api.app.domain.export_package import ExportFolderLayout, ExportPackageMode, plan_export_package
from services.api.app.domain.state import assert_transition_allowed
from services.api.app.repositories.interfaces import AuditEvent, RevisionRepository
from services.api.app.services.export_classification import classify_thread
from services.api.app.services.export_routing import plan_export_route
from services.api.app.services.export_writer import WrittenExportPackage, write_export_package
from services.api.app.services.rendering.json_artifacts import (
    build_manifest_json_artifact,
    build_metadata_json_artifact,
)
from services.api.app.services.rendering.manifest import plan_artifact_manifest
from services.api.app.services.rendering.pdf import PdfRendererAdapter, render_pdf_from_safe_thread
from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from services.api.app.services.revision_planner import RevisionPlanner, RevisionPlanStatus
from services.api.app.services.storage.attachments import (
    AttachmentContentProvider,
    NullAttachmentContentProvider,
    build_attachment_copy_artifacts,
)
from services.api.app.services.storage.rendered_artifacts import stage_and_verify_generated_artifacts
from services.api.app.services.storage.provider import StageAndVerifyResult, StoredArtifact
from services.api.app.services.storage.provider import StorageProvider


@dataclass(frozen=True)
class StorageVerificationOutcome:
    record: ArchiveRecordReference
    verification: VerificationSummary


@dataclass(frozen=True)
class ArchiveCompletionOutcome:
    record: ArchiveRecordReference
    completed_at: datetime


@dataclass(frozen=True)
class GmailFinalizationRequestOutcome:
    record: ArchiveRecordReference
    instructions: GmailFinalizationInstructions
    requested_at: datetime


@dataclass(frozen=True)
class GmailFinalizationCallbackOutcome:
    record: ArchiveRecordReference
    state: ArchiveState
    recorded_at: datetime


class ArchiveCoordinator:
    """Coordinates preservation while keeping Gmail finalization separate."""

    def __init__(self, repository: RevisionRepository) -> None:
        self.repository = repository

    def evaluate(self, request: ArchiveThreadRequest, identity: GoogleIdentity) -> ArchiveResult:
        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )

        request.validate(load_settings())
        plan = RevisionPlanner(self.repository).plan(identity.subject, request.thread)
        if plan.status == RevisionPlanStatus.DUPLICATE:
            return ArchiveResult(
                status=ArchiveStatus.DUPLICATE,
                record=plan.reference,
                gmail_finalization=GmailFinalizationInstructions(enabled=False),
            )

        return ArchiveResult(
            status=ArchiveStatus.FAILED,
            gmail_finalization=GmailFinalizationInstructions(enabled=False),
            error=ApiError(
                ErrorCategory.UNEXPECTED_INTERNAL,
                "Archive execution is not implemented in P2. Gmail finalization is disabled.",
            ),
        )

    def preserve(
        self,
        request: ArchiveThreadRequest,
        identity: GoogleIdentity,
        pdf_renderer: PdfRendererAdapter,
        storage_provider: StorageProvider,
        attachment_content_provider: AttachmentContentProvider | None = None,
    ) -> ArchiveResult:
        """Run the preservation pipeline through completion without mutating Gmail."""

        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )

        request.validate(load_settings())
        plan = RevisionPlanner(self.repository).plan(identity.subject, request.thread)
        if plan.status == RevisionPlanStatus.DUPLICATE:
            return ArchiveResult(
                status=ArchiveStatus.DUPLICATE,
                record=plan.reference,
                gmail_finalization=GmailFinalizationInstructions(enabled=False),
            )

        safe_thread = prepare_renderer_safe_thread(request.thread)
        active_attachment_provider = attachment_content_provider or NullAttachmentContentProvider()
        manifest = plan_artifact_manifest(plan.reference, safe_thread, attachment_source=request.thread)
        rendered_pdf = render_pdf_from_safe_thread(safe_thread, manifest, pdf_renderer)
        attachment_copies = build_attachment_copy_artifacts(request.thread, manifest, active_attachment_provider)
        metadata_json = build_metadata_json_artifact(request, safe_thread, manifest, attachment_copies)
        manifest_json = build_manifest_json_artifact(
            manifest,
            (rendered_pdf, *attachment_copies.artifacts, metadata_json),
            attachment_copies,
        )
        storage_result = stage_and_verify_generated_artifacts(
            plan.reference.record_id,
            (rendered_pdf, *attachment_copies.artifacts, metadata_json, manifest_json),
            storage_provider,
        )
        verified = self.record_verified_storage(identity, plan.gmail_thread_id, plan.reference, storage_result)
        completed = self.record_completed_preservation(identity, verified.record)

        return ArchiveResult(
            status=ArchiveStatus.PRESERVED,
            record=completed.record,
            verification=verified.verification,
            gmail_finalization=GmailFinalizationInstructions(enabled=False),
        )

    def preserve_export_package(
        self,
        request: ArchiveThreadRequest,
        identity: GoogleIdentity,
        export_root: Path | None = None,
        attachment_content_provider: AttachmentContentProvider | None = None,
        layout: ExportFolderLayout = ExportFolderLayout.DOMAIN_FIRST,
        sender_domain_override: str | None = None,
    ) -> ArchiveResult:
        """Run Preserve Mode through the local export package writer."""

        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )

        settings = load_settings()
        request.validate(settings)
        plan = RevisionPlanner(self.repository).plan(identity.subject, request.thread)
        if plan.status == RevisionPlanStatus.DUPLICATE:
            return ArchiveResult(
                status=ArchiveStatus.DUPLICATE,
                record=plan.reference,
                gmail_finalization=GmailFinalizationInstructions(enabled=False),
            )

        classification = classify_thread(request.thread)
        route = plan_export_route(
            request.thread,
            classification.category,
            layout=layout,
            sender_domain_override=sender_domain_override,
        )
        package = plan_export_package(
            plan.reference,
            request.thread,
            route.route,
            mode=ExportPackageMode.PRESERVE,
        )
        written = write_export_package(
            export_root or settings.storage_root,
            package,
            request.thread,
            attachment_content_provider,
        )
        verified = self.record_verified_storage(
            identity,
            plan.gmail_thread_id,
            plan.reference,
            _written_package_storage_result(written),
        )
        completed = self.record_completed_preservation(identity, verified.record)

        return ArchiveResult(
            status=ArchiveStatus.PRESERVED,
            record=completed.record,
            verification=verified.verification,
            gmail_finalization=GmailFinalizationInstructions(enabled=False),
        )

    def record_verified_storage(
        self,
        identity: GoogleIdentity,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
        storage_result: StageAndVerifyResult,
        verified_at: datetime | None = None,
    ) -> StorageVerificationOutcome:
        """Persist verified storage state without completing or finalizing Gmail."""

        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )
        if not storage_result.verified:
            raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Storage verification did not succeed.", "storage")

        active_verified_at = verified_at or datetime.now(UTC)
        created = self.repository.create_revision(identity.subject, gmail_thread_id, reference)
        for state in (ArchiveState.RENDERED, ArchiveState.STAGED, ArchiveState.VERIFIED):
            self.repository.append_audit_event(
                AuditEvent(record_id=created.record_id, state=state, occurred_at=active_verified_at)
            )

        return StorageVerificationOutcome(
            record=created,
            verification=VerificationSummary(
                verified=True,
                artifact_count=len(storage_result.artifacts),
                total_bytes=storage_result.total_bytes,
                verified_at=active_verified_at,
            ),
        )

    def record_completed_preservation(
        self,
        identity: GoogleIdentity,
        reference: ArchiveRecordReference,
        completed_at: datetime | None = None,
    ) -> ArchiveCompletionOutcome:
        """Record archive completion after the verified storage audit boundary."""

        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )

        audit_events = self.repository.list_audit_events(reference.record_id)
        if not audit_events:
            raise ApiError(
                ErrorCategory.DUPLICATE_CONFLICT,
                "Archive completion requires prior verified storage state.",
                "archive_state",
            )

        assert_transition_allowed(audit_events[-1].state, ArchiveState.COMPLETED)
        active_completed_at = completed_at or datetime.now(UTC)
        self.repository.append_audit_event(
            AuditEvent(record_id=reference.record_id, state=ArchiveState.COMPLETED, occurred_at=active_completed_at)
        )

        return ArchiveCompletionOutcome(record=reference, completed_at=active_completed_at)

    def request_gmail_finalization(
        self,
        identity: GoogleIdentity,
        record_id: str,
        preferences: ArchivePreferences,
        requested_at: datetime | None = None,
    ) -> GmailFinalizationRequestOutcome:
        """Enable Gmail finalization instructions only after archive completion."""

        reference = self._require_owned_record(identity, record_id)
        audit_events = self._require_audit_events(reference.record_id)
        assert_transition_allowed(audit_events[-1].state, ArchiveState.GMAIL_FINALIZATION_PENDING)

        active_requested_at = requested_at or datetime.now(UTC)
        self.repository.append_audit_event(
            AuditEvent(
                record_id=reference.record_id,
                state=ArchiveState.GMAIL_FINALIZATION_PENDING,
                occurred_at=active_requested_at,
            )
        )

        return GmailFinalizationRequestOutcome(
            record=reference,
            instructions=GmailFinalizationInstructions(
                mark_read=preferences.mark_read_after_preserve,
                archive=preferences.archive_after_preserve,
                enabled=True,
            ),
            requested_at=active_requested_at,
        )

    def record_gmail_finalization_callback(
        self,
        identity: GoogleIdentity,
        record_id: str,
        succeeded: bool,
        recorded_at: datetime | None = None,
    ) -> GmailFinalizationCallbackOutcome:
        """Record the add-on's Gmail mutation result after finalization is pending."""

        reference = self._require_owned_record(identity, record_id)
        audit_events = self._require_audit_events(reference.record_id)
        target_state = ArchiveState.GMAIL_FINALIZED if succeeded else ArchiveState.PRESERVED_GMAIL_FINALIZATION_FAILED
        assert_transition_allowed(audit_events[-1].state, target_state)

        active_recorded_at = recorded_at or datetime.now(UTC)
        self.repository.append_audit_event(
            AuditEvent(record_id=reference.record_id, state=target_state, occurred_at=active_recorded_at)
        )
        return GmailFinalizationCallbackOutcome(record=reference, state=target_state, recorded_at=active_recorded_at)

    def _require_owned_record(self, identity: GoogleIdentity, record_id: str) -> ArchiveRecordReference:
        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )

        reference = self.repository.find_by_record_id(identity.subject, record_id)
        if reference is None:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Archive record was not found for the verified owner.",
                "record_id",
            )
        return reference

    def _require_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        audit_events = self.repository.list_audit_events(record_id)
        if not audit_events:
            raise ApiError(
                ErrorCategory.DUPLICATE_CONFLICT,
                "Archive state history is required for Gmail finalization.",
                "archive_state",
            )
        return audit_events


def _written_package_storage_result(written: WrittenExportPackage) -> StageAndVerifyResult:
    return StageAndVerifyResult(
        verified=written.verified,
        artifacts=tuple(
            StoredArtifact(
                trusted_name=artifact.trusted_name,
                storage_path=artifact.relative_path,
                sha256=artifact.sha256 or "",
                size_bytes=artifact.size_bytes or 0,
            )
            for artifact in written.artifacts
            if artifact.generated
        ),
        total_bytes=written.total_bytes,
    )
