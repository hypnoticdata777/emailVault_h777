from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from uuid import UUID

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference
from services.api.app.domain.export_package import (
    ExportCategory,
    domain_first_route,
    plan_export_package,
)
from services.api.app.services.export_writer import write_export_package
from services.api.app.services.storage.attachments import MappingAttachmentContentProvider
from tests.fixture_loader import load_fixture


class ExportPackageWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.export_root = Path(self.temp_dir.name) / "EmailVault"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _reference(self, record_id: str = "record-export-writer") -> ArchiveRecordReference:
        return ArchiveRecordReference(
            vault_thread_id="vault-thread-export-writer",
            revision=1,
            record_id=record_id,
            snapshot_sha256="synthetic-export-writer-sha256",
        )

    def _request_with_attachment_bytes(self, content: bytes):
        request = load_fixture("plain_text")
        message = request.thread.messages[0]
        attachment = message.attachments[0]
        updated_attachment = replace(
            attachment,
            size_bytes=len(content),
            content_sha256=hashlib.sha256(content).hexdigest(),
        )
        updated_message = replace(message, attachments=(updated_attachment,))
        return replace(request, thread=replace(request.thread, messages=(updated_message,)))

    def _package(self, request, record_id: str = "record-export-writer"):
        uuid_values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000501"),
                UUID("00000000-0000-0000-0000-000000000502"),
                UUID("00000000-0000-0000-0000-000000000503"),
                UUID("00000000-0000-0000-0000-000000000504"),
                UUID("00000000-0000-0000-0000-000000000505"),
                UUID("00000000-0000-0000-0000-000000000506"),
                UUID("00000000-0000-0000-0000-000000000507"),
            )
        )
        return plan_export_package(
            self._reference(record_id),
            request.thread,
            domain_first_route("Receipts.Example.com", ExportCategory.AUTOMATED),
            uuid_factory=lambda: next(uuid_values),
        )

    def _provider(self, request, content: bytes) -> MappingAttachmentContentProvider:
        message = request.thread.messages[0]
        attachment = message.attachments[0]
        return MappingAttachmentContentProvider({(message.message_id, attachment.attachment_id): content})

    def test_write_export_package_creates_required_files_and_checksum_manifest(self) -> None:
        content = b"trusted synthetic pdf bytes"
        request = self._request_with_attachment_bytes(content)
        package = self._package(request)

        result = write_export_package(self.export_root, package, request.thread, self._provider(request, content))

        self.assertTrue(result.verified)
        self.assertEqual(result.relative_package_path, "receipts.example.com/automated/record-export-writer")
        self.assertTrue(result.package_path.is_dir())
        self.assertEqual(
            {artifact.trusted_name for artifact in result.artifacts},
            {
                "00000000-0000-0000-0000-000000000501.eml",
                "00000000-0000-0000-0000-000000000502.metadata.json",
                "00000000-0000-0000-0000-000000000503.manifest.json",
                "00000000-0000-0000-0000-000000000504.txt",
                "00000000-0000-0000-0000-000000000507.pdf",
            },
        )

        manifest_path = result.package_path / "00000000-0000-0000-0000-000000000503.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "email-vault.export-manifest.v1")
        self.assertEqual(manifest["package"]["route"]["relative_path"], "receipts.example.com/automated")

        generated_by_kind = {artifact["kind"]: artifact for artifact in manifest["artifacts"]}
        self.assertTrue(generated_by_kind["raw_eml"]["generated"])
        self.assertTrue(generated_by_kind["metadata_json"]["generated"])
        self.assertTrue(generated_by_kind["normalized_text"]["generated"])
        self.assertTrue(generated_by_kind["attachment"]["generated"])
        self.assertFalse(generated_by_kind["readable_html"]["generated"])
        self.assertFalse(generated_by_kind["readable_pdf"]["generated"])
        self.assertFalse(generated_by_kind["manifest_json"]["generated"])

        attachment_entry = generated_by_kind["attachment"]
        attachment_path = result.package_path / attachment_entry["trusted_name"]
        self.assertEqual(attachment_path.read_bytes(), content)
        self.assertEqual(attachment_entry["sha256"], hashlib.sha256(content).hexdigest())
        self.assertNotIn("receipt", attachment_entry["trusted_name"])

    def test_metadata_keeps_original_attachment_filename_as_metadata_only(self) -> None:
        content = b"trusted synthetic pdf bytes"
        request = self._request_with_attachment_bytes(content)
        package = self._package(request)

        result = write_export_package(self.export_root, package, request.thread, self._provider(request, content))

        metadata_path = result.package_path / "00000000-0000-0000-0000-000000000502.metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        attachment = metadata["thread"]["messages"][0]["attachments"][0]
        self.assertEqual(attachment["original_filename"], "receipt.pdf")
        self.assertFalse(any("receipt" in path.name for path in result.package_path.iterdir()))

    def test_missing_trusted_attachment_bytes_rejects_and_removes_partial_package(self) -> None:
        request = load_fixture("plain_text")
        package = self._package(request)

        with self.assertRaises(ApiError):
            write_export_package(self.export_root, package, request.thread)

        self.assertFalse((self.export_root / "receipts.example.com" / "automated" / "record-export-writer").exists())

    def test_attachment_checksum_mismatch_rejects_and_removes_partial_package(self) -> None:
        request = self._request_with_attachment_bytes(b"expected bytes")
        package = self._package(request)

        with self.assertRaises(ApiError):
            write_export_package(
                self.export_root,
                package,
                request.thread,
                self._provider(request, b"different bytes"),
            )

        self.assertFalse((self.export_root / "receipts.example.com" / "automated" / "record-export-writer").exists())

    def test_existing_export_package_directory_is_rejected(self) -> None:
        content = b"trusted synthetic pdf bytes"
        request = self._request_with_attachment_bytes(content)
        package = self._package(request)
        target = self.export_root / "receipts.example.com" / "automated" / "record-export-writer"
        target.mkdir(parents=True)

        with self.assertRaises(ApiError):
            write_export_package(self.export_root, package, request.thread, self._provider(request, content))


if __name__ == "__main__":
    unittest.main()
