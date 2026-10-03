from __future__ import annotations

import unittest

from services.api.app.domain.export_package import ExportFolderLayout, ExportPackageMode
from services.api.app.services.export_dry_run import PlannedGmailAction, plan_export_dry_run
from tests.fixture_loader import load_fixture


class ExportDryRunTests(unittest.TestCase):
    def _threads(self, *fixture_names: str):
        return tuple(load_fixture(name).thread for name in fixture_names)

    def test_preserve_mode_summarizes_categories_routes_and_export_only_actions(self) -> None:
        plan = plan_export_dry_run(
            self._threads(
                "newsletter_digest",
                "automated_notice",
                "bank_notice",
                "human_message",
                "attachments_heavy",
                "unknown_message",
            )
        )

        self.assertEqual(plan.mode, ExportPackageMode.PRESERVE)
        self.assertEqual(plan.summary.total_threads, 6)
        self.assertEqual(plan.summary.review_required_count, 4)
        self.assertEqual(
            plan.summary.by_category,
            {
                "attachments_heavy": 1,
                "automated": 1,
                "bank_financial": 1,
                "human": 1,
                "newsletter": 1,
                "unknown": 1,
            },
        )
        self.assertEqual(plan.summary.by_gmail_action, {"export_only": 6})
        self.assertEqual(plan.items[0].export_path, "example.com/newsletter")
        self.assertEqual(plan.items[0].planned_gmail_action, PlannedGmailAction.EXPORT_ONLY)

    def test_clean_inbox_mode_holds_review_required_items_before_gmail_cleanup(self) -> None:
        plan = plan_export_dry_run(
            self._threads("newsletter_digest", "automated_notice", "bank_notice", "unknown_message"),
            mode=ExportPackageMode.CLEAN_INBOX,
            layout=ExportFolderLayout.MIXED,
            mark_read=True,
            archive=True,
        )

        self.assertEqual(plan.summary.review_required_count, 2)
        self.assertEqual(
            plan.summary.by_gmail_action,
            {
                "label_mark_read_archive": 2,
                "needs_review": 2,
            },
        )
        self.assertEqual(plan.items[2].planned_gmail_action, PlannedGmailAction.NEEDS_REVIEW)
        self.assertTrue(plan.items[3].review_required)
        self.assertEqual(plan.items[3].export_path, "unknown/example.com")

    def test_sender_domain_override_is_reflected_in_review_summary_paths(self) -> None:
        plan = plan_export_dry_run(
            self._threads("newsletter_digest"),
            sender_domain_overrides={"gmail-thread-newsletter-001": "Daily.News.Example.com"},
        )

        self.assertEqual(plan.items[0].sender_domain, "daily.news.example.com")
        self.assertEqual(plan.items[0].export_path, "daily.news.example.com/newsletter")
        self.assertEqual(plan.summary.by_sender_domain, {"daily.news.example.com": 1})
        self.assertEqual(plan.summary.by_export_path, {"daily.news.example.com/newsletter": 1})

    def test_free_space_mode_never_plans_direct_delete_in_dry_run(self) -> None:
        plan = plan_export_dry_run(
            self._threads("newsletter_digest", "automated_notice", "bank_notice"),
            mode=ExportPackageMode.FREE_SPACE,
        )

        self.assertEqual(plan.summary.review_required_count, 3)
        self.assertEqual(
            plan.summary.by_gmail_action,
            {
                "needs_review": 1,
                "trash_review_queue": 2,
            },
        )
        self.assertEqual(plan.items[0].planned_gmail_action, PlannedGmailAction.TRASH_REVIEW_QUEUE)
        self.assertEqual(plan.items[2].planned_gmail_action, PlannedGmailAction.NEEDS_REVIEW)

    def test_empty_dry_run_returns_zero_counts(self) -> None:
        plan = plan_export_dry_run(())

        self.assertEqual(plan.summary.total_threads, 0)
        self.assertEqual(plan.summary.review_required_count, 0)
        self.assertEqual(plan.summary.by_category, {})
        self.assertEqual(plan.summary.by_gmail_action, {})


if __name__ == "__main__":
    unittest.main()
