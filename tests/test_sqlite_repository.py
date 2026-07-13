from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference, ArchiveState, snapshot_fingerprint
from services.api.app.repositories.interfaces import AuditEvent
from services.api.app.repositories.sqlite import SqliteRevisionRepository, sqlite_path_from_database_url
from tests.fixture_loader import load_fixture


class SqliteRevisionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "email-vault-test.db"
        self.repository = SqliteRevisionRepository(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _reference(self, revision: int = 1, fingerprint: str | None = None) -> ArchiveRecordReference:
        return ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=revision,
            record_id=f"record-{revision}",
            snapshot_sha256=fingerprint or snapshot_fingerprint(load_fixture("duplicate_snapshot").thread),
        )

    def test_create_and_find_revision_by_snapshot_hash(self) -> None:
        reference = self._reference()

        self.repository.create_revision("google-subject-example", "gmail-thread-example", reference)
        found = self.repository.find_by_snapshot_hash("google-subject-example", reference.snapshot_sha256)

        self.assertEqual(found, reference)

    def test_duplicate_snapshot_for_same_owner_is_rejected(self) -> None:
        reference = self._reference()
        self.repository.create_revision("google-subject-example", "gmail-thread-example", reference)

        with self.assertRaises(ApiError):
            self.repository.create_revision(
                "google-subject-example",
                "gmail-thread-example",
                ArchiveRecordReference(
                    vault_thread_id="vault-thread-example",
                    revision=2,
                    record_id="record-duplicate",
                    snapshot_sha256=reference.snapshot_sha256,
                ),
            )

    def test_same_snapshot_hash_can_exist_for_different_verified_owner(self) -> None:
        reference = self._reference()
        second_owner_reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-second-owner",
            revision=1,
            record_id="record-second-owner",
            snapshot_sha256=reference.snapshot_sha256,
        )

        self.repository.create_revision("google-subject-example", "gmail-thread-example", reference)
        self.repository.create_revision("other-google-subject-example", "gmail-thread-example", second_owner_reference)

        found = self.repository.find_by_snapshot_hash("other-google-subject-example", reference.snapshot_sha256)
        self.assertEqual(found, second_owner_reference)

    def test_next_revision_increments_per_owner_and_gmail_thread(self) -> None:
        original = self._reference(revision=1)
        updated = self._reference(
            revision=2,
            fingerprint=snapshot_fingerprint(load_fixture("updated_thread").thread),
        )

        self.assertEqual(self.repository.next_revision_for_thread("google-subject-example", "gmail-thread-example"), 1)
        self.repository.create_revision("google-subject-example", "gmail-thread-example", original)
        self.assertEqual(self.repository.next_revision_for_thread("google-subject-example", "gmail-thread-example"), 2)
        self.repository.create_revision("google-subject-example", "gmail-thread-example", updated)
        self.assertEqual(self.repository.next_revision_for_thread("google-subject-example", "gmail-thread-example"), 3)
        self.assertEqual(self.repository.next_revision_for_thread("other-google-subject-example", "gmail-thread-example"), 1)

    def test_find_latest_for_thread_returns_highest_revision(self) -> None:
        original = self._reference(revision=1)
        updated = self._reference(
            revision=2,
            fingerprint=snapshot_fingerprint(load_fixture("updated_thread").thread),
        )

        self.repository.create_revision("google-subject-example", "gmail-thread-example", original)
        self.repository.create_revision("google-subject-example", "gmail-thread-example", updated)

        latest = self.repository.find_latest_for_thread("google-subject-example", "gmail-thread-example")
        self.assertEqual(latest, updated)

    def test_find_by_record_id_is_owner_scoped(self) -> None:
        reference = self._reference()

        self.repository.create_revision("google-subject-example", "gmail-thread-example", reference)

        self.assertEqual(self.repository.find_by_record_id("google-subject-example", reference.record_id), reference)
        self.assertIsNone(self.repository.find_by_record_id("other-google-subject-example", reference.record_id))

    def test_audit_events_are_appended_in_order(self) -> None:
        reference = self._reference()
        self.repository.create_revision("google-subject-example", "gmail-thread-example", reference)

        self.repository.append_audit_event(
            AuditEvent(
                record_id=reference.record_id,
                state=ArchiveState.REQUESTED,
                occurred_at=datetime(2026, 7, 12, 18, 0, tzinfo=UTC),
            )
        )
        self.repository.append_audit_event(
            AuditEvent(
                record_id=reference.record_id,
                state=ArchiveState.VALIDATED,
                occurred_at=datetime(2026, 7, 12, 18, 1, tzinfo=UTC),
            )
        )

        events = self.repository.list_audit_events(reference.record_id)
        self.assertEqual([event.state for event in events], [ArchiveState.REQUESTED, ArchiveState.VALIDATED])

    def test_sqlite_path_is_derived_from_configured_database_url(self) -> None:
        self.assertEqual(sqlite_path_from_database_url("sqlite:///./email_vault.db"), Path("email_vault.db"))

        with self.assertRaises(ApiError):
            sqlite_path_from_database_url("postgresql://example.invalid/email_vault")


if __name__ == "__main__":
    unittest.main()
