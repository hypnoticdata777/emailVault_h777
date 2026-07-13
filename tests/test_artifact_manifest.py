from __future__ import annotations

import unittest
from uuid import UUID

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference
from services.api.app.services.rendering.manifest import (
    PlannedArtifactKind,
    PlannedArtifactStage,
    plan_artifact_manifest,
)
from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from tests.fixture_loader import load_fixture


class ArtifactManifestPlanningTests(unittest.TestCase):
    def _reference(self, record_id: str = "record-safe") -> ArchiveRecordReference:
        return ArchiveRecordReference(
            vault_thread_id="vault-thread-safe",
            revision=2,
            record_id=record_id,
            snapshot_sha256="synthetic-sha256",
        )

    def test_plan_artifact_manifest_uses_generated_names_and_safe_snapshot_metadata(self) -> None:
        safe_thread = prepare_renderer_safe_thread(load_fixture("tracking_pixel").thread)
        uuid_values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
                UUID("00000000-0000-0000-0000-000000000003"),
            )
        )

        manifest = plan_artifact_manifest(self._reference(), safe_thread, uuid_factory=lambda: next(uuid_values))

        self.assertEqual(manifest.record_id, "record-safe")
        self.assertEqual(manifest.vault_thread_id, "vault-thread-safe")
        self.assertEqual(manifest.revision, 2)
        self.assertEqual(manifest.thread_id, safe_thread.thread_id)
        self.assertEqual(manifest.gmail_thread_id, safe_thread.gmail_thread_id)
        self.assertEqual(manifest.message_count, 1)
        self.assertEqual(manifest.blocked_remote_resources, 1)
        self.assertEqual(
            [(artifact.kind, artifact.trusted_name, artifact.content_type, artifact.source_stage) for artifact in manifest.artifacts],
            [
                (
                    PlannedArtifactKind.PDF,
                    "00000000-0000-0000-0000-000000000001.pdf",
                    "application/pdf",
                    PlannedArtifactStage.RENDERED,
                ),
                (
                    PlannedArtifactKind.METADATA_JSON,
                    "00000000-0000-0000-0000-000000000002.metadata.json",
                    "application/json",
                    PlannedArtifactStage.METADATA,
                ),
                (
                    PlannedArtifactKind.MANIFEST_JSON,
                    "00000000-0000-0000-0000-000000000003.manifest.json",
                    "application/json",
                    PlannedArtifactStage.MANIFEST,
                ),
            ],
        )

    def test_plan_artifact_manifest_rejects_untrusted_record_id(self) -> None:
        safe_thread = prepare_renderer_safe_thread(load_fixture("plain_text").thread)

        with self.assertRaises(ApiError):
            plan_artifact_manifest(self._reference(record_id="../record-unsafe"), safe_thread)

    def test_plan_artifact_manifest_rejects_invalid_revision(self) -> None:
        safe_thread = prepare_renderer_safe_thread(load_fixture("plain_text").thread)
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-safe",
            revision=0,
            record_id="record-safe",
            snapshot_sha256="synthetic-sha256",
        )

        with self.assertRaises(ApiError):
            plan_artifact_manifest(reference, safe_thread)


if __name__ == "__main__":
    unittest.main()
