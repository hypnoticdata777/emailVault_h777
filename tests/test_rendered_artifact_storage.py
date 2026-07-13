from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.services.rendering.pdf import RenderedPdfArtifact
from services.api.app.services.storage.provider import LocalFilesystemStorageProvider, StageAndVerifyRequest
from services.api.app.services.storage.rendered_artifacts import (
    stage_and_verify_generated_artifacts,
    stage_and_verify_rendered_pdf,
)


class FailingStorageProvider:
    def stage_and_verify(self, request: StageAndVerifyRequest):
        del request
        raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Synthetic storage failure.", "artifacts")


class RenderedArtifactStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.storage_root = self.root / "vault-storage"
        self.temp_root = self.root / "stage-work"
        self.temp_root.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _rendered_pdf(self, content: bytes = b"%PDF-1.4\n% synthetic staged pdf\n%%EOF") -> RenderedPdfArtifact:
        return RenderedPdfArtifact(
            trusted_name="00000000-0000-0000-0000-000000000301.pdf",
            content_type="application/pdf",
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )

    def test_stage_and_verify_rendered_pdf_writes_verified_storage_without_completion_state(self) -> None:
        provider = LocalFilesystemStorageProvider(self.storage_root)
        rendered_pdf = self._rendered_pdf()

        result = stage_and_verify_rendered_pdf("record-rendered", rendered_pdf, provider, temp_root=self.temp_root)

        stored_path = self.storage_root / "record-rendered" / rendered_pdf.trusted_name
        self.assertTrue(result.verified)
        self.assertEqual(result.total_bytes, rendered_pdf.size_bytes)
        self.assertEqual(result.artifacts[0].trusted_name, rendered_pdf.trusted_name)
        self.assertEqual(result.artifacts[0].sha256, rendered_pdf.sha256)
        self.assertEqual(stored_path.read_bytes(), rendered_pdf.content)
        self.assertEqual(tuple(self.temp_root.iterdir()), ())

    def test_stage_and_verify_rendered_pdf_cleans_temp_workspace_on_storage_failure(self) -> None:
        with self.assertRaises(ApiError) as context:
            stage_and_verify_rendered_pdf(
                "record-rendered",
                self._rendered_pdf(),
                FailingStorageProvider(),
                temp_root=self.temp_root,
            )

        self.assertEqual(context.exception.category, ErrorCategory.STORAGE_VERIFICATION)
        self.assertEqual(tuple(self.temp_root.iterdir()), ())

    def test_stage_and_verify_generated_artifacts_writes_multiple_outputs(self) -> None:
        provider = LocalFilesystemStorageProvider(self.storage_root)
        rendered_pdf = self._rendered_pdf()
        metadata = RenderedPdfArtifact(
            trusted_name="00000000-0000-0000-0000-000000000302.metadata.json",
            content_type="application/json",
            content=b"{\"schema_version\":\"email-vault.metadata.v1\"}\n",
            sha256=hashlib.sha256(b"{\"schema_version\":\"email-vault.metadata.v1\"}\n").hexdigest(),
            size_bytes=len(b"{\"schema_version\":\"email-vault.metadata.v1\"}\n"),
        )

        result = stage_and_verify_generated_artifacts(
            "record-rendered",
            (rendered_pdf, metadata),
            provider,
            temp_root=self.temp_root,
        )

        self.assertTrue(result.verified)
        self.assertEqual([artifact.trusted_name for artifact in result.artifacts], [rendered_pdf.trusted_name, metadata.trusted_name])
        self.assertEqual((self.storage_root / "record-rendered" / metadata.trusted_name).read_bytes(), metadata.content)
        self.assertEqual(tuple(self.temp_root.iterdir()), ())


if __name__ == "__main__":
    unittest.main()
