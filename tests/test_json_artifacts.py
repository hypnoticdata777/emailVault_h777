from __future__ import annotations

import hashlib
import json
import unittest
from uuid import UUID

from services.api.app.domain.contracts import ArchiveRecordReference
from services.api.app.services.rendering.json_artifacts import (
    build_manifest_json_artifact,
    build_metadata_json_artifact,
)
from services.api.app.services.rendering.manifest import PlannedArtifactKind, plan_artifact_manifest
from services.api.app.services.rendering.pdf import RenderedPdfArtifact
from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from tests.fixture_loader import load_fixture


class JsonArtifactTests(unittest.TestCase):
    def _manifest(self):
        uuid_values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000401"),
                UUID("00000000-0000-0000-0000-000000000402"),
                UUID("00000000-0000-0000-0000-000000000403"),
            )
        )
        request = load_fixture("plain_text")
        safe_thread = prepare_renderer_safe_thread(request.thread)
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-json",
            revision=1,
            record_id="record-json",
            snapshot_sha256="synthetic-sha256",
        )
        manifest = plan_artifact_manifest(reference, safe_thread, uuid_factory=lambda: next(uuid_values))
        return request, safe_thread, manifest

    def test_metadata_json_artifact_records_sanitized_thread_and_attachment_boundary(self) -> None:
        request, safe_thread, manifest = self._manifest()

        artifact = build_metadata_json_artifact(request, safe_thread, manifest)
        payload = json.loads(artifact.content.decode("utf-8"))

        self.assertEqual(artifact.trusted_name, "00000000-0000-0000-0000-000000000402.metadata.json")
        self.assertEqual(artifact.content_type, "application/json")
        self.assertEqual(artifact.sha256, hashlib.sha256(artifact.content).hexdigest())
        self.assertEqual(payload["schema_version"], "email-vault.metadata.v1")
        self.assertEqual(payload["record"]["record_id"], "record-json")
        self.assertEqual(payload["thread"]["message_count"], len(safe_thread.messages))
        self.assertEqual(payload["thread"]["messages"][0]["plain_text_size"], len("Plain synthetic message for Email Vault."))
        self.assertEqual(payload["thread"]["messages"][0]["attachments"][0]["original_filename"], "receipt.pdf")
        self.assertEqual(payload["thread"]["messages"][0]["attachments"][0]["copy_status"], "descriptor_only")
        self.assertNotIn("storage_path", payload["thread"]["messages"][0]["attachments"][0])
        self.assertEqual(payload["attachment_copy"]["status"], "descriptor_only")

    def test_manifest_json_artifact_lists_generated_outputs_without_claiming_attachment_copy(self) -> None:
        request, _safe_thread, manifest = self._manifest()
        metadata = build_metadata_json_artifact(request, prepare_renderer_safe_thread(request.thread), manifest)
        rendered_pdf = RenderedPdfArtifact(
            trusted_name="00000000-0000-0000-0000-000000000401.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 synthetic",
            sha256=hashlib.sha256(b"%PDF-1.4 synthetic").hexdigest(),
            size_bytes=len(b"%PDF-1.4 synthetic"),
        )

        artifact = build_manifest_json_artifact(manifest, (rendered_pdf, metadata))
        payload = json.loads(artifact.content.decode("utf-8"))

        generated_by_kind = {item["kind"]: item for item in payload["artifacts"]}
        self.assertEqual(artifact.trusted_name, "00000000-0000-0000-0000-000000000403.manifest.json")
        self.assertTrue(generated_by_kind[PlannedArtifactKind.PDF.value]["generated"])
        self.assertEqual(generated_by_kind[PlannedArtifactKind.PDF.value]["sha256"], rendered_pdf.sha256)
        self.assertTrue(generated_by_kind[PlannedArtifactKind.METADATA_JSON.value]["generated"])
        self.assertFalse(generated_by_kind[PlannedArtifactKind.MANIFEST_JSON.value]["generated"])
        self.assertEqual(payload["attachment_copy"]["status"], "descriptor_only")


if __name__ == "__main__":
    unittest.main()
