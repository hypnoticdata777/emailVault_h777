from __future__ import annotations

import unittest

from datetime import UTC, datetime

from services.api.app.auth.identity import GoogleIdentity
from services.api.app.domain.contracts import (
    ApiError,
    ArchivePreferences,
    ArchiveRecordReference,
    ArchiveState,
    ArchiveStatus,
    snapshot_fingerprint,
)
from services.api.app.repositories.interfaces import AuditEvent
from services.api.app.services.archive import ArchiveCoordinator
from services.api.app.services.storage.provider import StageAndVerifyResult, StoredArtifact
from tests.fixture_loader import load_fixture


class FakeRevisionRepository:
    def __init__(self, duplicate: ArchiveRecordReference | None = None) -> None:
        self.duplicate = duplicate
        self.lookup_owner_subjects: list[str] = []
        self.created_revisions: list[tuple[str, str, ArchiveRecordReference]] = []
        self.audit_events: list[AuditEvent] = []
        self.records_by_owner_and_id: dict[tuple[str, str], ArchiveRecordReference] = {}

    def create_revision(
        self,
        owner_subject: str,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
    ) -> ArchiveRecordReference:
        self.created_revisions.append((owner_subject, gmail_thread_id, reference))
        self.records_by_owner_and_id[(owner_subject, reference.record_id)] = reference
        return reference

    def find_by_snapshot_hash(self, owner_subject: str, snapshot_sha256: str) -> ArchiveRecordReference | None:
        self.lookup_owner_subjects.append(owner_subject)
        if self.duplicate and self.duplicate.snapshot_sha256 == snapshot_sha256:
            return self.duplicate
        return None

    def find_latest_for_thread(self, owner_subject: str, gmail_thread_id: str) -> ArchiveRecordReference | None:
        return None

    def find_by_record_id(self, owner_subject: str, record_id: str) -> ArchiveRecordReference | None:
        return self.records_by_owner_and_id.get((owner_subject, record_id))

    def next_revision_for_thread(self, owner_subject: str, gmail_thread_id: str) -> int:
        return 1

    def append_audit_event(self, event: AuditEvent) -> None:
        self.audit_events.append(event)

    def list_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        return tuple(event for event in self.audit_events if event.record_id == record_id)


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

    def test_verified_storage_records_revision_and_verified_audit_without_gmail_finalization(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-verified",
            snapshot_sha256="synthetic-sha256",
        )
        storage_result = StageAndVerifyResult(
            verified=True,
            artifacts=(
                StoredArtifact(
                    trusted_name="00000000-0000-0000-0000-000000000301.pdf",
                    storage_path="record-verified/00000000-0000-0000-0000-000000000301.pdf",
                    sha256="synthetic-artifact-sha256",
                    size_bytes=34,
                ),
            ),
            total_bytes=34,
        )
        verified_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)

        outcome = ArchiveCoordinator(repository).record_verified_storage(
            self._identity(),
            "gmail-thread-example",
            reference,
            storage_result,
            verified_at=verified_at,
        )

        self.assertEqual(outcome.record, reference)
        self.assertTrue(outcome.verification.verified)
        self.assertEqual(outcome.verification.artifact_count, 1)
        self.assertEqual(outcome.verification.total_bytes, 34)
        self.assertEqual(outcome.verification.verified_at, verified_at)
        self.assertEqual(repository.created_revisions, [("google-subject-example", "gmail-thread-example", reference)])
        self.assertEqual(
            [event.state for event in repository.audit_events],
            [ArchiveState.RENDERED, ArchiveState.STAGED, ArchiveState.VERIFIED],
        )
        self.assertNotIn(ArchiveState.COMPLETED, [event.state for event in repository.audit_events])
        self.assertNotIn(ArchiveState.GMAIL_FINALIZATION_PENDING, [event.state for event in repository.audit_events])

    def test_completed_preservation_appends_completed_after_verified_storage(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-completed",
            snapshot_sha256="synthetic-sha256",
        )
        verified_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
        completed_at = datetime(2026, 7, 13, 12, 1, tzinfo=UTC)
        repository.audit_events.extend(
            (
                AuditEvent(record_id=reference.record_id, state=ArchiveState.RENDERED, occurred_at=verified_at),
                AuditEvent(record_id=reference.record_id, state=ArchiveState.STAGED, occurred_at=verified_at),
                AuditEvent(record_id=reference.record_id, state=ArchiveState.VERIFIED, occurred_at=verified_at),
            )
        )

        outcome = ArchiveCoordinator(repository).record_completed_preservation(
            self._identity(),
            reference,
            completed_at=completed_at,
        )

        self.assertEqual(outcome.record, reference)
        self.assertEqual(outcome.completed_at, completed_at)
        self.assertEqual(
            [event.state for event in repository.audit_events],
            [ArchiveState.RENDERED, ArchiveState.STAGED, ArchiveState.VERIFIED, ArchiveState.COMPLETED],
        )
        self.assertNotIn(ArchiveState.GMAIL_FINALIZATION_PENDING, [event.state for event in repository.audit_events])

    def test_completed_preservation_requires_verified_state_without_writes(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-staged-only",
            snapshot_sha256="synthetic-sha256",
        )
        staged_at = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
        repository.audit_events.extend(
            (
                AuditEvent(record_id=reference.record_id, state=ArchiveState.RENDERED, occurred_at=staged_at),
                AuditEvent(record_id=reference.record_id, state=ArchiveState.STAGED, occurred_at=staged_at),
            )
        )

        with self.assertRaises(ApiError):
            ArchiveCoordinator(repository).record_completed_preservation(self._identity(), reference)

        self.assertEqual(
            [event.state for event in repository.audit_events],
            [ArchiveState.RENDERED, ArchiveState.STAGED],
        )

    def test_gmail_finalization_request_requires_completed_archive_and_returns_instructions(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-ready-for-gmail",
            snapshot_sha256="synthetic-sha256",
        )
        repository.create_revision("google-subject-example", "gmail-thread-example", reference)
        completed_at = datetime(2026, 7, 13, 12, 1, tzinfo=UTC)
        requested_at = datetime(2026, 7, 13, 12, 2, tzinfo=UTC)
        repository.audit_events.append(
            AuditEvent(record_id=reference.record_id, state=ArchiveState.COMPLETED, occurred_at=completed_at)
        )

        outcome = ArchiveCoordinator(repository).request_gmail_finalization(
            self._identity(),
            reference.record_id,
            ArchivePreferences(category="Receipts", mark_read_after_preserve=True, archive_after_preserve=True),
            requested_at=requested_at,
        )

        self.assertEqual(outcome.record, reference)
        self.assertEqual(outcome.requested_at, requested_at)
        self.assertTrue(outcome.instructions.enabled)
        self.assertTrue(outcome.instructions.mark_read)
        self.assertTrue(outcome.instructions.archive)
        self.assertEqual(
            [event.state for event in repository.audit_events],
            [ArchiveState.COMPLETED, ArchiveState.GMAIL_FINALIZATION_PENDING],
        )

    def test_gmail_finalization_request_rejects_before_completed_without_writes(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-not-complete",
            snapshot_sha256="synthetic-sha256",
        )
        repository.create_revision("google-subject-example", "gmail-thread-example", reference)
        repository.audit_events.append(
            AuditEvent(
                record_id=reference.record_id,
                state=ArchiveState.VERIFIED,
                occurred_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
            )
        )

        with self.assertRaises(ApiError):
            ArchiveCoordinator(repository).request_gmail_finalization(
                self._identity(),
                reference.record_id,
                ArchivePreferences(category="Receipts"),
            )

        self.assertEqual([event.state for event in repository.audit_events], [ArchiveState.VERIFIED])

    def test_gmail_finalization_callback_records_success_after_pending_state(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-gmail-finalized",
            snapshot_sha256="synthetic-sha256",
        )
        repository.create_revision("google-subject-example", "gmail-thread-example", reference)
        pending_at = datetime(2026, 7, 13, 12, 2, tzinfo=UTC)
        recorded_at = datetime(2026, 7, 13, 12, 3, tzinfo=UTC)
        repository.audit_events.append(
            AuditEvent(
                record_id=reference.record_id,
                state=ArchiveState.GMAIL_FINALIZATION_PENDING,
                occurred_at=pending_at,
            )
        )

        outcome = ArchiveCoordinator(repository).record_gmail_finalization_callback(
            self._identity(),
            reference.record_id,
            succeeded=True,
            recorded_at=recorded_at,
        )

        self.assertEqual(outcome.record, reference)
        self.assertEqual(outcome.state, ArchiveState.GMAIL_FINALIZED)
        self.assertEqual(outcome.recorded_at, recorded_at)
        self.assertEqual(
            [event.state for event in repository.audit_events],
            [ArchiveState.GMAIL_FINALIZATION_PENDING, ArchiveState.GMAIL_FINALIZED],
        )

    def test_gmail_finalization_callback_rejects_without_pending_state(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-no-pending-gmail",
            snapshot_sha256="synthetic-sha256",
        )
        repository.create_revision("google-subject-example", "gmail-thread-example", reference)
        repository.audit_events.append(
            AuditEvent(
                record_id=reference.record_id,
                state=ArchiveState.COMPLETED,
                occurred_at=datetime(2026, 7, 13, 12, 1, tzinfo=UTC),
            )
        )

        with self.assertRaises(ApiError):
            ArchiveCoordinator(repository).record_gmail_finalization_callback(
                self._identity(),
                reference.record_id,
                succeeded=True,
            )

        self.assertEqual([event.state for event in repository.audit_events], [ArchiveState.COMPLETED])

    def test_unverified_storage_result_is_rejected_without_writes(self) -> None:
        repository = FakeRevisionRepository()
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-example",
            revision=1,
            record_id="record-unverified",
            snapshot_sha256="synthetic-sha256",
        )

        with self.assertRaises(ApiError):
            ArchiveCoordinator(repository).record_verified_storage(
                self._identity(),
                "gmail-thread-example",
                reference,
                StageAndVerifyResult(verified=False, artifacts=(), total_bytes=0),
            )

        self.assertEqual(repository.created_revisions, [])
        self.assertEqual(repository.audit_events, [])


if __name__ == "__main__":
    unittest.main()
