from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference, ErrorCategory
from services.api.app.services.rendering.manifest import plan_artifact_manifest
from services.api.app.services.rendering.pdf import (
    PdfRenderPolicy,
    build_renderer_html,
    render_pdf_from_safe_thread,
)
from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from tests.fixture_loader import load_fixture


class RecordingPdfAdapter:
    def __init__(self, content: bytes = b"%PDF-1.4\n% synthetic scaffold\n%%EOF") -> None:
        self.content = content
        self.html_content: str | None = None
        self.output_path: Path | None = None
        self.policy: PdfRenderPolicy | None = None

    def render_pdf(self, html_content: str, output_path: Path, policy: PdfRenderPolicy) -> None:
        self.html_content = html_content
        self.output_path = output_path
        self.policy = policy
        output_path.write_bytes(self.content)


class FailingPdfAdapter:
    def render_pdf(self, html_content: str, output_path: Path, policy: PdfRenderPolicy) -> None:
        del html_content, output_path, policy
        raise RuntimeError("synthetic renderer failure")


class PdfRendererScaffoldTests(unittest.TestCase):
    def _manifest(self, safe_thread):
        reference = ArchiveRecordReference(
            vault_thread_id="vault-thread-safe",
            revision=1,
            record_id="record-safe",
            snapshot_sha256="synthetic-sha256",
        )
        uuid_values = iter(
            (
                UUID("00000000-0000-0000-0000-000000000101"),
                UUID("00000000-0000-0000-0000-000000000102"),
                UUID("00000000-0000-0000-0000-000000000103"),
            )
        )
        return plan_artifact_manifest(reference, safe_thread, uuid_factory=lambda: next(uuid_values))

    def test_renderer_html_uses_sanitized_body_not_raw_script(self) -> None:
        safe_thread = prepare_renderer_safe_thread(load_fixture("malicious_html").thread)

        html_content = build_renderer_html(safe_thread)

        self.assertIn("Safe text remains.", html_content)
        self.assertNotIn("<script", html_content)
        self.assertNotIn("alert", html_content)

    def test_render_pdf_uses_blocked_network_policy_and_returns_verified_bytes(self) -> None:
        safe_thread = prepare_renderer_safe_thread(load_fixture("tracking_pixel").thread)
        adapter = RecordingPdfAdapter()

        with tempfile.TemporaryDirectory() as temp_root_name:
            temp_root = Path(temp_root_name)
            result = render_pdf_from_safe_thread(safe_thread, self._manifest(safe_thread), adapter, temp_root=temp_root)
            remaining_workspaces = tuple(temp_root.iterdir())

        self.assertEqual(result.trusted_name, "00000000-0000-0000-0000-000000000101.pdf")
        self.assertEqual(result.content_type, "application/pdf")
        self.assertEqual(result.size_bytes, len(adapter.content))
        self.assertEqual(result.content, adapter.content)
        self.assertIsNotNone(adapter.policy)
        self.assertFalse(adapter.policy.javascript_enabled)
        self.assertTrue(adapter.policy.block_network)
        self.assertIn("image", adapter.policy.blocked_resource_types)
        self.assertIn("fetch", adapter.policy.blocked_resource_types)
        self.assertNotIn("tracker.example.com", adapter.html_content or "")
        self.assertEqual(remaining_workspaces, ())

    def test_render_pdf_cleans_workspace_on_adapter_failure(self) -> None:
        safe_thread = prepare_renderer_safe_thread(load_fixture("plain_text").thread)

        with tempfile.TemporaryDirectory() as temp_root_name:
            temp_root = Path(temp_root_name)
            with self.assertRaises(ApiError) as context:
                render_pdf_from_safe_thread(safe_thread, self._manifest(safe_thread), FailingPdfAdapter(), temp_root=temp_root)
            remaining_workspaces = tuple(temp_root.iterdir())

        self.assertEqual(context.exception.category, ErrorCategory.SANITIZATION_RENDERING)
        self.assertEqual(remaining_workspaces, ())


if __name__ == "__main__":
    unittest.main()
