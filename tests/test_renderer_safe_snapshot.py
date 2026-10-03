from __future__ import annotations

import unittest

from services.api.app.services.rendering.snapshot import prepare_renderer_safe_thread
from tests.fixture_loader import load_fixture


class RendererSafeSnapshotTests(unittest.TestCase):
    def test_renderer_safe_snapshot_uses_sanitized_html_and_plain_text_fallback(self) -> None:
        thread = load_fixture("malicious_html").thread

        safe_thread = prepare_renderer_safe_thread(thread)
        message = safe_thread.messages[0]

        self.assertEqual(safe_thread.thread_id, thread.thread_id)
        self.assertIsNotNone(message.safe_html)
        self.assertNotIn("<script", message.safe_html or "")
        self.assertNotIn("alert", message.safe_html or "")
        self.assertIn("Safe text remains.", message.plain_text)

    def test_renderer_safe_snapshot_preserves_plain_text_without_html(self) -> None:
        thread = load_fixture("plain_text").thread

        safe_thread = prepare_renderer_safe_thread(thread)
        message = safe_thread.messages[0]

        self.assertIsNone(message.safe_html)
        self.assertIn("Plain synthetic message", message.plain_text)
        self.assertEqual(message.labels, ("INBOX",))

    def test_renderer_safe_snapshot_reports_blocked_remote_resources(self) -> None:
        thread = load_fixture("tracking_pixel").thread

        safe_thread = prepare_renderer_safe_thread(thread)

        self.assertEqual(safe_thread.blocked_remote_resources, 1)
        self.assertEqual(safe_thread.messages[0].blocked_remote_resources, 1)
        self.assertNotIn("tracker.example.com", safe_thread.messages[0].safe_html or "")


if __name__ == "__main__":
    unittest.main()

