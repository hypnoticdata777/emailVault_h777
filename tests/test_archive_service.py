from __future__ import annotations

import unittest

from services.api.app.auth.identity import GoogleIdentity
from services.api.app.domain.contracts import (
    ApiError,
    ArchiveRecordReference,
    ArchiveState,
    ArchiveStatus,
    snapshot_fingerprint,
)
from services.api.app.repositories.interfaces import AuditEvent
from services.api.app.services.archive import ArchiveCoordinator
from tests.fixture_loader import load_fixture


class FakeRevisionRepository:
    def __init__(self, duplicate: ArchiveRecordReference | None = None) -> None:
        self.duplicate = duplicate
        self.lookup_owner_subjects: list[str] = []

    def create_revision(
        self,
        owner_subject: str,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
    ) -> ArchiveRecordReference:
        raise NotImplementedError

    def find_by_snapshot_hash(self, owner_subject: str, snapshot_sha256: str) -> ArchiveRecordReference | None:
        self.lookup_owner_subjects.append(owner_subject)
        if self.duplicate and self.duplicate.snapshot_sha256 == snapshot_sha256:
            return self.duplicate
        return None

    def find_latest_for_thread(self, owner_subject: str, gmail_thread_id: str) -> ArchiveRecordReference | None:
        return None

    def next_revision_for_thread(self, owner_subject: str, gmail_thread_id: str) -> int:
        return 1

    def append_audit_event(self, event: AuditEvent) -> None:
        raise NotImplementedError

    def list_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        return ()


class ArchiveCoordinatorTests(unittest.TestCase):
    def _identity(self, email_verified: bool = True) -> GoogleIdentity:
        return GoogleIdentity(
            subject="google-subject-example",
            email="owner@example.com",
            email_verified=email_verified,
        )

    def test_duplicate_snapshot_returns_existing_record_without_gmail_finalization(self) -> None:
        request = load_fixture("duplicate_snapshot")
        existing = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-existing",
            snapshot_sha256=snapshot_fingerprint(request.thread),
        )
        repository = FakeRevisionRepository(duplicate=existing)

        result = ArchiveCoordinator(repository).evaluate(request, self._identity())

        self.assertEqual(result.status, ArchiveStatus.DUPLICATE)
        self.assertEqual(result.record, existing)
        self.assertFalse(result.gmail_finalization.enabled)
        self.assertEqual(repository.lookup_owner_subjects, ["google-subject-example"])

    def test_new_snapshot_returns_controlled_failed_stub_without_writes(self) -> None:
        result = ArchiveCoordinator(FakeRevisionRepository()).evaluate(load_fixture("plain_text"), self._identity())

        self.assertEqual(result.status, ArchiveStatus.FAILED)
        self.assertIsNone(result.record)
        self.assertFalse(result.gmail_finalization.enabled)
        self.assertIsNotNone(result.error)

    def test_unverified_google_email_is_rejected(self) -> None:
        with self.assertRaises(ApiError):
            ArchiveCoordinator(FakeRevisionRepository()).evaluate(load_fixture("plain_text"), self._identity(False))


if __name__ == "__main__":
    unittest.main()
