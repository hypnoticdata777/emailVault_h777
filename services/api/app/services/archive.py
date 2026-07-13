from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from services.api.app.auth.identity import GoogleIdentity
from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import (
    ApiError,
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
