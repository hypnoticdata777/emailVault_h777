from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from uuid import UUID, uuid4

from services.api.app.domain.contracts import ArchiveRecordReference, ThreadSnapshot, snapshot_fingerprint
from services.api.app.repositories.interfaces import RevisionRepository


class RevisionPlanStatus(StrEnum):
    DUPLICATE = "DUPLICATE"
    NEW_REVISION = "NEW_REVISION"


@dataclass(frozen=True)
class RevisionPlan:
    status: RevisionPlanStatus
    reference: ArchiveRecordReference
    gmail_thread_id: str


class RevisionPlanner:
    """Plans duplicate or new-revision decisions without writing completion state.

    This service is intentionally side-effect-light: it may read repository state
    and generate server-owned IDs, but it does not create archive records. Later
    storage verification work will decide when a planned reference is safe to
    persist as a real revision.
    """

    def __init__(
        self,
        repository: RevisionRepository,
        uuid_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self.repository = repository
        self.uuid_factory = uuid_factory

    def plan(self, owner_subject: str, thread: ThreadSnapshot) -> RevisionPlan:
        fingerprint = snapshot_fingerprint(thread)
        duplicate = self.repository.find_by_snapshot_hash(owner_subject, fingerprint)
        if duplicate:
            return RevisionPlan(
                status=RevisionPlanStatus.DUPLICATE,
                reference=duplicate,
                gmail_thread_id=thread.gmail_thread_id,
            )

        latest = self.repository.find_latest_for_thread(owner_subject, thread.gmail_thread_id)
        revision = self.repository.next_revision_for_thread(owner_subject, thread.gmail_thread_id)
        vault_thread_id = latest.vault_thread_id if latest else f"vault-thread-{self.uuid_factory()}"

        return RevisionPlan(
            status=RevisionPlanStatus.NEW_REVISION,
            reference=ArchiveRecordReference(
                vault_thread_id=vault_thread_id,
                revision=revision,
                record_id=f"record-{self.uuid_factory()}",
                snapshot_sha256=fingerprint,
            ),
            gmail_thread_id=thread.gmail_thread_id,
        )
