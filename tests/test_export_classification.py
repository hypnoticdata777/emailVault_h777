from __future__ import annotations

import unittest
from dataclasses import replace

from services.api.app.domain.export_package import ExportCategory
from services.api.app.services.export_classification import (
    ClassificationReason,
    classify_thread,
)
from tests.fixture_loader import load_fixture


class ExportClassificationTests(unittest.TestCase):
    def _reasons_for(self, fixture_name: str) -> set[str]:
        result = classify_thread(load_fixture(fixture_name).thread)
        return {evidence.reason for evidence in result.evidence}

    def test_newsletter_fixture_classifies_from_list_headers_without_review(self) -> None:
        result = classify_thread(load_fixture("newsletter_digest").thread)

        self.assertEqual(result.category, ExportCategory.NEWSLETTER)
        self.assertFalse(result.review_required)
        self.assertIn(ClassificationReason.NEWSLETTER_HEADER, self._reasons_for("newsletter_digest"))

    def test_automated_fixture_classifies_from_headers_and_no_reply_sender_without_review(self) -> None:
        result = classify_thread(load_fixture("automated_notice").thread)

        self.assertEqual(result.category, ExportCategory.AUTOMATED)
        self.assertFalse(result.review_required)
        self.assertIn(ClassificationReason.AUTOMATED_HEADER, self._reasons_for("automated_notice"))
        self.assertIn(ClassificationReason.NO_REPLY_SENDER, self._reasons_for("automated_notice"))

    def test_bank_fixture_classifies_as_review_required_financial_mail(self) -> None:
        result = classify_thread(load_fixture("bank_notice").thread)

        self.assertEqual(result.category, ExportCategory.BANK_FINANCIAL)
        self.assertTrue(result.review_required)
        self.assertEqual(result.evidence[0].reason, ClassificationReason.BANK_KEYWORD)

    def test_human_fixture_classifies_as_review_required_human_mail(self) -> None:
        result = classify_thread(load_fixture("human_message").thread)

        self.assertEqual(result.category, ExportCategory.HUMAN)
        self.assertTrue(result.review_required)
        self.assertEqual(result.evidence[0].reason, ClassificationReason.HUMAN_QUESTION)

    def test_attachments_heavy_fixture_classifies_as_review_required_bulk_attachment_mail(self) -> None:
        result = classify_thread(load_fixture("attachments_heavy").thread)

        self.assertEqual(result.category, ExportCategory.ATTACHMENTS_HEAVY)
        self.assertTrue(result.review_required)
        self.assertEqual(result.evidence[0].reason, ClassificationReason.ATTACHMENT_COUNT)

    def test_unknown_fixture_defaults_to_review_required_unknown_mail(self) -> None:
        result = classify_thread(load_fixture("unknown_message").thread)

        self.assertEqual(result.category, ExportCategory.UNKNOWN)
        self.assertTrue(result.review_required)
        self.assertEqual(result.evidence[0].reason, ClassificationReason.UNKNOWN)

    def test_newsletter_headers_win_before_attachment_volume(self) -> None:
        request = load_fixture("newsletter_digest")
        attachment_fixture = load_fixture("attachments_heavy").thread.messages[0]
        newsletter_message = request.thread.messages[0]
        thread = replace(
            request.thread,
            messages=(replace(newsletter_message, attachments=attachment_fixture.attachments),),
        )

        result = classify_thread(thread)

        self.assertEqual(result.category, ExportCategory.NEWSLETTER)
        self.assertFalse(result.review_required)

    def test_no_reply_sender_wins_before_human_question_text(self) -> None:
        request = load_fixture("human_message")
        message = request.thread.messages[0]
        thread = replace(
            request.thread,
            messages=(
                replace(
                    message,
                    from_participant=replace(message.from_participant, email="no-reply@example.com"),
                ),
            ),
        )

        result = classify_thread(thread)

        self.assertEqual(result.category, ExportCategory.AUTOMATED)
        self.assertFalse(result.review_required)
        self.assertEqual(result.evidence[0].reason, ClassificationReason.NO_REPLY_SENDER)


if __name__ == "__main__":
    unittest.main()
