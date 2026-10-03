from __future__ import annotations

import unittest
from dataclasses import replace

from services.api.app.domain.contracts import ApiError
from services.api.app.domain.export_package import ExportCategory, ExportFolderLayout
from services.api.app.services.export_routing import (
    ExportRouteReason,
    normalize_sender_domain,
    plan_export_route,
    primary_sender_domain,
)
from tests.fixture_loader import load_fixture


class ExportRoutingTests(unittest.TestCase):
    def test_plan_export_route_uses_primary_sender_domain_for_domain_first_layout(self) -> None:
        request = load_fixture("plain_text")

        plan = plan_export_route(request.thread, ExportCategory.NEWSLETTER)

        self.assertEqual(plan.thread_id, "thread-plain-001")
        self.assertEqual(plan.gmail_thread_id, "gmail-thread-plain-001")
        self.assertEqual(plan.sender_domain, "example.com")
        self.assertEqual(plan.layout, ExportFolderLayout.DOMAIN_FIRST)
        self.assertEqual(plan.route.relative_parts, ("example.com", "newsletter"))
        self.assertEqual(plan.reason, ExportRouteReason.SENDER_DOMAIN)

    def test_plan_export_route_supports_category_first_layout(self) -> None:
        request = load_fixture("plain_text")

        plan = plan_export_route(
            request.thread,
            ExportCategory.BANK_FINANCIAL,
            layout=ExportFolderLayout.CATEGORY_FIRST,
        )

        self.assertEqual(plan.route.relative_parts, ("bank_financial", "example.com"))
        self.assertEqual(plan.route.relative_path, "bank_financial/example.com")

    def test_plan_export_route_supports_sender_domain_override(self) -> None:
        request = load_fixture("plain_text")

        plan = plan_export_route(
            request.thread,
            ExportCategory.AUTOMATED,
            sender_domain_override="Alerts.Example-Bank.COM",
        )

        self.assertEqual(plan.sender_domain, "alerts.example-bank.com")
        self.assertEqual(plan.route.relative_parts, ("alerts.example-bank.com", "automated"))
        self.assertEqual(plan.reason, ExportRouteReason.SENDER_DOMAIN_OVERRIDE)

    def test_mixed_layout_routes_review_first_categories_before_domain(self) -> None:
        request = load_fixture("plain_text")

        plan = plan_export_route(
            request.thread,
            ExportCategory.NEEDS_REVIEW,
            layout=ExportFolderLayout.MIXED,
        )

        self.assertEqual(plan.route.layout, ExportFolderLayout.CATEGORY_FIRST)
        self.assertEqual(plan.route.relative_parts, ("needs_review", "example.com"))
        self.assertEqual(plan.reason, ExportRouteReason.REVIEW_FIRST_CATEGORY)

    def test_mixed_layout_routes_known_categories_domain_first(self) -> None:
        request = load_fixture("plain_text")

        plan = plan_export_route(
            request.thread,
            ExportCategory.HUMAN,
            layout=ExportFolderLayout.MIXED,
        )

        self.assertEqual(plan.route.layout, ExportFolderLayout.DOMAIN_FIRST)
        self.assertEqual(plan.route.relative_parts, ("example.com", "human"))

    def test_primary_sender_domain_uses_most_common_sender_domain_and_ties_first_seen(self) -> None:
        request = load_fixture("plain_text")
        first_message = request.thread.messages[0]
        second_message = replace(
            first_message,
            message_id="msg-second",
            gmail_message_id="gmail-msg-second",
            from_participant=replace(first_message.from_participant, email="updates@example.org"),
        )
        third_message = replace(
            first_message,
            message_id="msg-third",
            gmail_message_id="gmail-msg-third",
            from_participant=replace(first_message.from_participant, email="alerts@example.org"),
        )
        thread = replace(request.thread, messages=(first_message, second_message, third_message))

        self.assertEqual(primary_sender_domain(thread), "example.org")

    def test_normalize_sender_domain_rejects_invalid_domain(self) -> None:
        self.assertEqual(normalize_sender_domain("Sender@News.Example.COM"), "news.example.com")
        with self.assertRaises(ApiError):
            normalize_sender_domain("sender@localhost")


if __name__ == "__main__":
    unittest.main()
