from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from services.api.app.domain.contracts import ArchiveRecordReference, ArchiveState


@dataclass(frozen=True)
class AuditEvent:
    record_id: str
    state: ArchiveState
    occurred_at: datetime


class RevisionRepository(Protocol):
    """Persistence boundary for duplicate detection, revisions, and audit state.

    Implementations must derive ownership from the verified Google subject passed
    by the service layer. They must not accept or persist a client-supplied owner
    id from the archive request payload.
    """

    def create_revision(
        self,
        owner_subject: str,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
    ) -> ArchiveRecordReference:
        raise NotImplementedError

    def find_by_snapshot_hash(self, owner_subject: str, snapshot_sha256: str) -> ArchiveRecordReference | None:
        raise NotImplementedError

    def find_latest_for_thread(self, owner_subject: str, gmail_thread_id: str) -> ArchiveRecordReference | None:
        raise NotImplementedError

    def find_by_record_id(self, owner_subject: str, record_id: str) -> ArchiveRecordReference | None:
        raise NotImplementedError

    def next_revision_for_thread(self, owner_subject: str, gmail_thread_id: str) -> int:
        raise NotImplementedError

    def append_audit_event(self, event: AuditEvent) -> None:
        raise NotImplementedError

    def list_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        raise NotImplementedError
