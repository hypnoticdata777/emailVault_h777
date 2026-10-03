from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from services.api.app.domain.contracts import ApiError
from services.api.app.services.storage.provider import (
    ArtifactToStore,
    LocalFilesystemStorageProvider,
    StageAndVerifyRequest,
)


class LocalFilesystemStorageProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "vault-storage"
        self.source_dir = Path(self.temp_dir.name) / "sources"
        self.source_dir.mkdir()
        self.provider = LocalFilesystemStorageProvider(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _artifact(
        self,
        trusted_name: str = "metadata.json",
        source_name: str = "source.bin",
        content: bytes = b'{"synthetic": true}',
    ) -> ArtifactToStore:
        source_path = self.source_dir / source_name
        source_path.write_bytes(content)
        return ArtifactToStore(
            trusted_name=trusted_name,
            source_path=source_path,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )

    def test_stage_and_verify_copies_artifact_and_reports_verified_result(self) -> None:
        result = self.provider.stage_and_verify(
            StageAndVerifyRequest(record_id="record-safe", artifacts=(self._artifact(),))
        )

        self.assertTrue(result.verified)
        self.assertEqual(result.total_bytes, 19)
        self.assertEqual(result.artifacts[0].storage_path, str(Path("record-safe") / "metadata.json"))
        self.assertTrue((self.root / "record-safe" / "metadata.json").is_file())

    def test_stage_and_verify_rejects_original_filename_as_nested_path(self) -> None:
        with self.assertRaises(ApiError):
            self.provider.stage_and_verify(
                StageAndVerifyRequest(
                    record_id="record-safe",
                    artifacts=(self._artifact(trusted_name="original/receipt.pdf", content=b"unsafe"),),
                )
            )

    def test_stage_and_verify_removes_partial_record_directory_on_checksum_failure(self) -> None:
        artifact = self._artifact(content=b"expected")
        broken = ArtifactToStore(
            trusted_name=artifact.trusted_name,
            source_path=artifact.source_path,
            sha256=hashlib.sha256(b"different").hexdigest(),
            size_bytes=artifact.size_bytes,
        )

        with self.assertRaises(ApiError):
            self.provider.stage_and_verify(StageAndVerifyRequest(record_id="record-safe", artifacts=(broken,)))

        self.assertFalse((self.root / "record-safe").exists())

    def test_stage_and_verify_rejects_untrusted_record_id(self) -> None:
        with self.assertRaises(ApiError):
            self.provider.stage_and_verify(
                StageAndVerifyRequest(record_id="../record-safe", artifacts=(self._artifact(),))
            )


if __name__ == "__main__":
    unittest.main()

