from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from uuid import UUID

from services.api.app.domain.contracts import ApiError
from services.api.app.services.rendering.manifest import plan_artifact_manifest
from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from services.api.app.services.storage.attachments import (
    MappingAttachmentContentProvider,
    NullAttachmentContentProvider,
    build_attachment_copy_artifacts,
)
from tests.fixture_loader import load_fixture


class StaticAttachmentContentProvider:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def fetch_attachment_content(self, message, attachment) -> bytes:
        del message, attachment
        return self.content


class AttachmentCopyTests(unittest.TestCase):
    def _request_with_attachment_sha(self, content: bytes):
        request = load_fixture("plain_text")
        message = request.thread.messages[0]
        attachment = message.attachments[0]
        updated_attachment = replace(attachment, content_sha256=hashlib.sha256(content).hexdigest(), size_bytes=len(content))
        updated_message = replace(message, attachments=(updated_attachment,))
        updated_thread = replace(request.thread, messages=(updated_message,))
        return replace(request, thread=updated_thread)

    def _manifest(self, request):
        uuid_values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000501"),
                UUID("00000000-0000-0000-0000-000000000502"),
                UUID("00000000-0000-0000-0000-000000000503"),
                UUID("00000000-0000-0000-0000-000000000504"),
            )
        )
        safe_thread = prepare_renderer_safe_thread(request.thread)
        from services.api.app.domain.contracts import ArchiveRecordReference

        return plan_artifact_manifest(
            ArchiveRecordReference(
                vault_thread_id="vault-thread-attachment",
                revision=1,
                record_id="record-attachment",
                snapshot_sha256="synthetic-sha256",
            ),
            safe_thread,
            uuid_factory=lambda: next(uuid_values),
            attachment_source=request.thread,
        )

    def test_copy_artifacts_remain_descriptor_only_without_trusted_bytes(self) -> None:
        request = load_fixture("plain_text")
        result = build_attachment_copy_artifacts(request.thread, self._manifest(request), NullAttachmentContentProvider())

        self.assertEqual(result.artifacts, ())
        self.assertEqual(result.statuses[0].copy_status, "descriptor_only")
        self.assertIsNone(result.statuses[0].trusted_name)

    def test_copy_artifacts_include_trusted_bytes_with_server_generated_name(self) -> None:
        content = b"trusted pdf bytes"
        request = self._request_with_attachment_sha(content)

        result = build_attachment_copy_artifacts(
            request.thread,
            self._manifest(request),
            StaticAttachmentContentProvider(content),
        )

        self.assertEqual(len(result.artifacts), 1)
        self.assertEqual(result.artifacts[0].trusted_name, "00000000-0000-0000-0000-000000000504.pdf")
        self.assertEqual(result.artifacts[0].original_filename, "receipt.pdf")
        self.assertEqual(result.artifacts[0].content, content)
        self.assertEqual(result.statuses[0].copy_status, "copied")
        self.assertEqual(result.statuses[0].trusted_name, result.artifacts[0].trusted_name)
        self.assertEqual(result.statuses[0].sha256, hashlib.sha256(content).hexdigest())

    def test_copy_artifacts_use_mapped_payload_bytes_before_fallback(self) -> None:
        content = b"trusted mapped bytes"
        request = self._request_with_attachment_sha(content)
        message = request.thread.messages[0]
        attachment = message.attachments[0]
        provider = MappingAttachmentContentProvider(
            {(message.message_id, attachment.attachment_id): content},
            StaticAttachmentContentProvider(b"different fallback bytes"),
        )

        result = build_attachment_copy_artifacts(request.thread, self._manifest(request), provider)

        self.assertEqual(result.artifacts[0].content, content)
        self.assertEqual(result.statuses[0].copy_status, "copied")

    def test_copy_artifacts_reject_checksum_mismatch(self) -> None:
        request = self._request_with_attachment_sha(b"expected")

        with self.assertRaises(ApiError):
            build_attachment_copy_artifacts(
                request.thread,
                self._manifest(request),
                StaticAttachmentContentProvider(b"different"),
            )


if __name__ == "__main__":
    unittest.main()
