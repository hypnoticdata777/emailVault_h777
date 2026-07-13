from __future__ import annotations

import unittest

from services.api.app.services.sanitization.html import html_to_plain_text, sanitize_email_html
from services.api.app.services.sanitization.normalize import (
    SanitizedBodySource,
    normalize_message_bodies,
    normalize_thread_bodies,
)
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

    def test_unsafe_javascript_link_is_removed_but_text_is_preserved(self) -> None:
        result = sanitize_email_html('<a href="javascript:steal()">Open synthetic link</a>')

        self.assertNotIn("javascript:", result.html)
        self.assertIn("<a>", result.html)
        self.assertEqual(result.plain_text, "Open synthetic link")

    def test_cid_inline_image_source_is_allowed(self) -> None:
        result = sanitize_email_html('<img src="cid:inline-image-001" alt="Inline chart">')

        self.assertIn('src="cid:inline-image-001"', result.html)
        self.assertEqual(result.blocked_remote_resources, 0)

    def test_unknown_tags_are_removed_but_text_is_preserved(self) -> None:
        result = sanitize_email_html("<custom-card>Visible synthetic text</custom-card>")

        self.assertNotIn("custom-card", result.html)
        self.assertEqual(result.plain_text, "Visible synthetic text")

    def test_malformed_html_is_handled_safely(self) -> None:
        result = sanitize_email_html("<p>Open <strong>bold")

        self.assertIn("Open", result.plain_text)
        self.assertIn("bold", result.plain_text)

    def test_html_message_normalization_adds_plain_text_fallback(self) -> None:
        message = load_fixture("basic_html").thread.messages[0]

        normalized = normalize_message_bodies(message)

        self.assertEqual([body.mime_type for body in normalized.bodies], ["text/html", "text/plain"])
        self.assertEqual(normalized.bodies[0].source, SanitizedBodySource.SANITIZED_HTML)
        self.assertEqual(normalized.bodies[1].source, SanitizedBodySource.PLAIN_TEXT_FALLBACK)
        self.assertIn("Hello synthetic archive.", normalized.bodies[1].content)

    def test_plain_text_message_normalization_preserves_original_text(self) -> None:
        message = load_fixture("plain_text").thread.messages[0]

        normalized = normalize_message_bodies(message)

        self.assertEqual(len(normalized.bodies), 1)
        self.assertEqual(normalized.bodies[0].source, SanitizedBodySource.ORIGINAL_TEXT)
        self.assertIn("Plain synthetic message", normalized.bodies[0].content)

    def test_thread_normalization_sums_blocked_remote_resources(self) -> None:
        thread = load_fixture("tracking_pixel").thread

        normalized = normalize_thread_bodies(thread)

        self.assertEqual(normalized.blocked_remote_resources, 1)
        self.assertEqual(normalized.messages[0].blocked_remote_resources, 1)

    def test_table_heavy_email_keeps_table_text_and_strips_unsafe_attributes(self) -> None:
        result = sanitize_email_html(
            '<table style="background:url(https://tracker.example.com/bg.png)">'
            '<tr onclick="steal()">'
            '<th colspan="2">Synthetic invoice</th>'
            "</tr>"
            "<tr><td>Item</td><td>Total</td></tr>"
            "</table>"
        )

        self.assertIn("<table>", result.html)
        self.assertIn('<th colspan="2">Synthetic invoice</th>', result.html)
        self.assertNotIn("style", result.html)
        self.assertNotIn("onclick", result.html)
        self.assertNotIn("tracker.example.com", result.html)
        self.assertIn("Synthetic invoice", result.plain_text)
        self.assertIn("Total", result.plain_text)

    def test_attachment_adjacent_file_link_loses_href_but_keeps_label(self) -> None:
        result = sanitize_email_html('<a href="file:///C:/secret/invoice.pdf">invoice.pdf</a>')

        self.assertNotIn("file://", result.html)
        self.assertIn("<a>invoice.pdf</a>", result.html)
        self.assertEqual(result.plain_text, "invoice.pdf")

    def test_attachment_adjacent_data_link_loses_href_but_keeps_label(self) -> None:
        result = sanitize_email_html('<a href="data:text/html;base64,PHNjcmlwdD4=">download report</a>')

        self.assertNotIn("data:text", result.html)
        self.assertIn("<a>download report</a>", result.html)
        self.assertEqual(result.plain_text, "download report")

    def test_form_like_controls_are_removed_but_visible_text_remains(self) -> None:
        result = sanitize_email_html(
            '<form action="https://example.com/collect">'
            '<label>Approval code</label>'
            '<input name="code" value="secret">'
            '<button>Submit</button>'
            "</form>"
        )

        self.assertNotIn("<form", result.html)
        self.assertNotIn("<input", result.html)
        self.assertNotIn("<button", result.html)
        self.assertIn("Approval code", result.plain_text)
        self.assertIn("Submit", result.plain_text)


if __name__ == "__main__":
    unittest.main()
