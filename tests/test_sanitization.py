from __future__ import annotations

import unittest

from services.api.app.services.sanitization.html import html_to_plain_text, sanitize_email_html
from tests.fixture_loader import load_fixture


class SanitizationTests(unittest.TestCase):
    def test_malicious_html_removes_script_content_and_keeps_safe_text(self) -> None:
        body = load_fixture("malicious_html").thread.messages[0].bodies[0].content

        result = sanitize_email_html(body)

        self.assertNotIn("<script", result.html)
        self.assertNotIn("alert", result.html)
        self.assertIn("Safe text remains.", result.html)
        self.assertIn("Safe text remains.", result.plain_text)
        self.assertIn("script", result.removed_tags)

    def test_tracking_pixel_blocks_remote_image_source(self) -> None:
        body = load_fixture("tracking_pixel").thread.messages[0].bodies[0].content

        result = sanitize_email_html(body)

        self.assertEqual(result.blocked_remote_resources, 1)
        self.assertNotIn("tracker.example.com", result.html)
        self.assertIn("<img", result.html)
        self.assertIn("Hello", result.plain_text)

    def test_event_handlers_and_styles_are_removed(self) -> None:
        result = sanitize_email_html('<p onclick="steal()" style="background:url(https://example.com/x)">Hi</p>')

        self.assertNotIn("onclick", result.html)
        self.assertNotIn("style", result.html)
        self.assertNotIn("https://example.com/x", result.html)
        self.assertEqual(result.plain_text, "Hi")

    def test_plain_text_fallback_collapses_blocks(self) -> None:
        self.assertEqual(html_to_plain_text("<div>Hello</div><p>World</p>"), "Hello\nWorld")


if __name__ == "__main__":
    unittest.main()

