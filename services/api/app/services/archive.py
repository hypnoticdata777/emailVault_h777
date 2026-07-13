from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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
from services.api.app.domain.state import assert_transition_allowed
from services.api.app.repositories.interfaces import AuditEvent, RevisionRepository
from services.api.app.services.revision_planner import RevisionPlanner, RevisionPlanStatus
from services.api.app.services.storage.provider import StageAndVerifyResult


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
    """Coordinates the P2 archive decision without performing preservation.

    Later phases will add sanitizer, renderer, storage verification, and durable
    state writes here. For now, the coordinator proves the ordering: authenticate,
    validate, fingerprint, check duplicate, and keep Gmail finalization disabled.
    """

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
