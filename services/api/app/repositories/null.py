from __future__ import annotations

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference, ErrorCategory
from services.api.app.repositories.interfaces import AuditEvent


class NullRevisionRepository:
    """Route-safe P2 repository placeholder.

    It performs duplicate lookups as empty and refuses writes. This lets the API
    route exercise identity, validation, and orchestration without pretending
    storage-backed preservation has been implemented.
    """

    def create_revision(
        self,
        owner_subject: str,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
    ) -> ArchiveRecordReference:
        del owner_subject, gmail_thread_id, reference
        raise ApiError(ErrorCategory.STORAGE_UNAVAILABLE, "Revision persistence is not configured.")

    def find_by_snapshot_hash(self, owner_subject: str, snapshot_sha256: str) -> ArchiveRecordReference | None:
        del owner_subject, snapshot_sha256
        return None

    def next_revision_for_thread(self, owner_subject: str, gmail_thread_id: str) -> int:
        del owner_subject, gmail_thread_id
        raise ApiError(ErrorCategory.STORAGE_UNAVAILABLE, "Revision persistence is not configured.")

    def append_audit_event(self, event: AuditEvent) -> None:
        del event
        raise ApiError(ErrorCategory.STORAGE_UNAVAILABLE, "Revision persistence is not configured.")

    def list_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        del record_id
        return ()
