from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from services.api.app.domain.contracts import ArchiveRecordReference
from services.api.app.services.rendering.manifest import plan_artifact_manifest
from services.api.app.services.rendering.pdf import render_pdf_from_safe_thread
from services.api.app.services.rendering.playwright_adapter import PlaywrightPdfRendererAdapter
from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from tests.fixture_loader import load_fixture


SMOKE_ENV_VAR = "EMAIL_VAULT_RUN_RENDERER_SMOKE"


class PlaywrightRendererSmokeTests(unittest.TestCase):
    def test_real_playwright_adapter_renders_pdf_when_enabled(self) -> None:
        if os.getenv(SMOKE_ENV_VAR) != "1":
            self.skipTest(f"Set {SMOKE_ENV_VAR}=1 to run the browser-backed renderer smoke test.")
        try:
            import playwright.sync_api  # noqa: F401
        except ImportError:
            self.skipTest("Playwright is not installed. Install with: python -m pip install -e \".[renderer]\"")

        safe_thread = prepare_renderer_safe_thread(load_fixture("basic_html").thread)
        manifest = plan_artifact_manifest(_reference(), safe_thread, uuid_factory=_uuid_factory())
        adapter = PlaywrightPdfRendererAdapter(chromium_launch_options={"headless": True})

        with tempfile.TemporaryDirectory() as temp_root_name:
            temp_root = Path(temp_root_name)
            result = render_pdf_from_safe_thread(safe_thread, manifest, adapter, temp_root=temp_root)
            remaining_workspaces = tuple(temp_root.iterdir())

        self.assertEqual(result.trusted_name, "00000000-0000-0000-0000-000000000201.pdf")
        self.assertEqual(result.content_type, "application/pdf")
        self.assertTrue(result.content.startswith(b"%PDF"))
        self.assertGreater(result.size_bytes, 0)
        self.assertEqual(remaining_workspaces, ())


def _reference() -> ArchiveRecordReference:
    return ArchiveRecordReference(
        vault_thread_id="vault-thread-smoke",
        revision=1,
        record_id="record-smoke",
        snapshot_sha256="synthetic-smoke-sha256",
    )


def _uuid_factory():
    uuid_values = iter(
        (
            UUID("00000000-0000-0000-0000-000000000201"),
            UUID("00000000-0000-0000-0000-000000000202"),
            UUID("00000000-0000-0000-0000-000000000203"),
        )
    )
    return lambda: next(uuid_values)


if __name__ == "__main__":
    unittest.main()
