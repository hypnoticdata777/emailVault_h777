from __future__ import annotations

import unittest
from uuid import UUID

from services.api.app.domain.contracts import ArchiveRecordReference, snapshot_fingerprint
from services.api.app.repositories.interfaces import AuditEvent
from services.api.app.services.revision_planner import RevisionPlanner, RevisionPlanStatus
from tests.fixture_loader import load_fixture


class PlanningRepository:
    def __init__(
        self,
        duplicate: ArchiveRecordReference | None = None,
        latest: ArchiveRecordReference | None = None,
        next_revision: int = 1,
    ) -> None:
        self.duplicate = duplicate
        self.latest = latest
        self.next_revision = next_revision
        self.created_records: list[ArchiveRecordReference] = []

    def create_revision(
        self,
        owner_subject: str,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
    ) -> ArchiveRecordReference:
        self.created_records.append(reference)
        return reference

    def find_by_snapshot_hash(self, owner_subject: str, snapshot_sha256: str) -> ArchiveRecordReference | None:
        if self.duplicate and self.duplicate.snapshot_sha256 == snapshot_sha256:
            return self.duplicate
        return None

    def find_latest_for_thread(self, owner_subject: str, gmail_thread_id: str) -> ArchiveRecordReference | None:
        return self.latest

    def next_revision_for_thread(self, owner_subject: str, gmail_thread_id: str) -> int:
        return self.next_revision

    def append_audit_event(self, event: AuditEvent) -> None:
        raise NotImplementedError

    def list_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        return ()


class FixedUuidFactory:
    def __init__(self) -> None:
        self.values = [
            UUID("00000000-0000-0000-0000-000000000101"),
            UUID("00000000-0000-0000-0000-000000000202"),
        ]

    def __call__(self) -> UUID:
        return self.values.pop(0)


class RevisionPlannerTests(unittest.TestCase):
    def test_duplicate_snapshot_reuses_existing_reference_without_writes(self) -> None:
        thread = load_fixture("duplicate_snapshot").thread
        existing = ArchiveRecordReference(
            vault_thread_id="vault-thread-existing",
            revision=1,
            record_id="record-existing",
            snapshot_sha256=snapshot_fingerprint(thread),
        )
        repository = PlanningRepository(duplicate=existing)

        plan = RevisionPlanner(repository, FixedUuidFactory()).plan("google-subject-example", thread)

        self.assertEqual(plan.status, RevisionPlanStatus.DUPLICATE)
        self.assertEqual(plan.reference, existing)
        self.assertEqual(repository.created_records, [])

    def test_new_gmail_thread_gets_server_generated_vault_and_record_ids(self) -> None:
        thread = load_fixture("plain_text").thread
        repository = PlanningRepository(next_revision=1)

        plan = RevisionPlanner(repository, FixedUuidFactory()).plan("google-subject-example", thread)

        self.assertEqual(plan.status, RevisionPlanStatus.NEW_REVISION)
        self.assertEqual(plan.reference.vault_thread_id, "vault-thread-00000000-0000-0000-0000-000000000101")
        self.assertEqual(plan.reference.record_id, "record-00000000-0000-0000-0000-000000000202")
        self.assertEqual(plan.reference.revision, 1)
        self.assertEqual(repository.created_records, [])

    def test_updated_thread_reuses_existing_vault_thread_and_increments_revision(self) -> None:
        latest = ArchiveRecordReference(
            vault_thread_id="vault-thread-existing",
            revision=1,
            record_id="record-existing",
            snapshot_sha256=snapshot_fingerprint(load_fixture("duplicate_snapshot").thread),
        )
        repository = PlanningRepository(latest=latest, next_revision=2)

        plan = RevisionPlanner(repository, FixedUuidFactory()).plan(
            "google-subject-example",
            load_fixture("updated_thread").thread,
        )

        self.assertEqual(plan.status, RevisionPlanStatus.NEW_REVISION)
        self.assertEqual(plan.reference.vault_thread_id, "vault-thread-existing")
        self.assertEqual(plan.reference.revision, 2)
        self.assertEqual(plan.reference.record_id, "record-00000000-0000-0000-0000-000000000101")
        self.assertEqual(repository.created_records, [])


if __name__ == "__main__":
    unittest.main()
