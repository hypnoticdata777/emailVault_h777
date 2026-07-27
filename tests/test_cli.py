from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from services.api.app import cli


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "emails"


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.database_url = f"sqlite:///{self.root / 'email-vault-cli.db'}"
        self.export_root = self.root / "EmailVault"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run(self, *args: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = cli.main(list(args))
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_init_db_bootstraps_configured_sqlite_database(self) -> None:
        exit_code, stdout, stderr = self._run("init-db")

        self.assertEqual(exit_code, 0)
        self.assertIn("Initialized Email Vault SQLite database", stdout)
        self.assertEqual(stderr, "")

    def test_preserve_local_writes_package_and_prints_json_summary(self) -> None:
        exit_code, stdout, stderr = self._run(
            "preserve-local",
            "--request",
            str(FIXTURE_ROOT / "unknown_message.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
            "--json",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "PRESERVED")
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["artifact_count"], 4)
        self.assertFalse(payload["gmail_finalization_enabled"])
        self.assertTrue(Path(payload["package_path"]).is_dir())
        self.assertEqual(payload["relative_package_path"], f"example.com/{payload['record_id']}")

    def test_preserve_local_duplicate_returns_existing_record_without_second_package(self) -> None:
        first_exit_code, first_stdout, _first_stderr = self._run(
            "preserve-local",
            "--request",
            str(FIXTURE_ROOT / "unknown_message.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
            "--json",
        )
        second_exit_code, second_stdout, second_stderr = self._run(
            "preserve-local",
            "--request",
            str(FIXTURE_ROOT / "unknown_message.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
            "--json",
        )

        first_payload = json.loads(first_stdout)
        second_payload = json.loads(second_stdout)
        self.assertEqual(first_exit_code, 0)
        self.assertEqual(second_exit_code, 0)
        self.assertEqual(second_stderr, "")
        self.assertEqual(second_payload["status"], "DUPLICATE")
        self.assertEqual(second_payload["record_id"], first_payload["record_id"])
        self.assertIsNone(second_payload["package_path"])
        self.assertIsNone(second_payload["verified"])

    def test_preserve_local_reports_controlled_error_for_missing_attachment_bytes(self) -> None:
        exit_code, stdout, stderr = self._run(
            "preserve-local",
            "--request",
            str(FIXTURE_ROOT / "plain_text.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("storage_unavailable", stderr)
        self.assertFalse(any(self.export_root.rglob("record-*")) if self.export_root.exists() else False)

    def test_clean_inbox_review_prints_batch_plan_without_gmail_mutation(self) -> None:
        exit_code, stdout, stderr = self._run(
            "clean-inbox-review",
            "--request",
            str(FIXTURE_ROOT / "newsletter_digest.json"),
            "--request",
            str(FIXTURE_ROOT / "bank_notice.json"),
            "--request",
            str(FIXTURE_ROOT / "unknown_message.json"),
            "--layout",
            "mixed",
            "--mark-read",
            "--json",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["mode"], "clean_inbox")
        self.assertEqual(payload["layout"], "mixed")
        self.assertTrue(payload["mark_read"])
        self.assertTrue(payload["archive"])
        self.assertFalse(payload["gmail_mutation_enabled"])
        self.assertEqual(payload["summary"]["total_threads"], 3)
        self.assertEqual(payload["summary"]["review_required_count"], 2)
        self.assertEqual(
            payload["summary"]["by_gmail_action"],
            {
                "label_mark_read_archive": 1,
                "needs_review": 2,
            },
        )
        self.assertEqual(payload["items"][0]["category"], "newsletter")
        self.assertTrue(payload["items"][0]["approved_by_default"])
        self.assertFalse(payload["items"][1]["approved_by_default"])
        self.assertEqual(payload["items"][2]["planned_gmail_action"], "needs_review")

    def test_clean_inbox_review_accepts_sender_domain_override(self) -> None:
        exit_code, stdout, stderr = self._run(
            "clean-inbox-review",
            "--request",
            str(FIXTURE_ROOT / "newsletter_digest.json"),
            "--sender-domain-override",
            "gmail-thread-newsletter-001=daily.news.example.com",
            "--json",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["items"][0]["sender_domain"], "daily.news.example.com")
        self.assertEqual(payload["items"][0]["export_path"], "daily.news.example.com/newsletter")

    def test_record_clean_inbox_intent_adds_audit_marker_without_enabling_gmail_mutation(self) -> None:
        preserve_exit_code, preserve_stdout, preserve_stderr = self._run(
            "preserve-local",
            "--request",
            str(FIXTURE_ROOT / "unknown_message.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
            "--json",
        )
        record_id = json.loads(preserve_stdout)["record_id"]

        exit_code, stdout, stderr = self._run(
            "record-clean-inbox-intent",
            "--record-id",
            record_id,
            "--database-url",
            self.database_url,
            "--mark-read",
            "--json",
        )

        self.assertEqual(preserve_exit_code, 0)
        self.assertEqual(preserve_stderr, "")
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["record_id"], record_id)
        self.assertEqual(payload["state"], "CLEAN_INBOX_INTENT_RECORDED")
        self.assertTrue(payload["gmail_finalization"]["mark_read"])
        self.assertTrue(payload["gmail_finalization"]["archive"])
        self.assertFalse(payload["gmail_finalization"]["enabled"])

    def test_record_clean_inbox_intent_rejects_unknown_or_unowned_record(self) -> None:
        exit_code, stdout, stderr = self._run(
            "record-clean-inbox-intent",
            "--record-id",
            "record-does-not-exist",
            "--database-url",
            self.database_url,
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("authentication_authorization", stderr)

    def test_local_batch_preserves_reviews_and_records_only_approvable_intents(self) -> None:
        exit_code, stdout, stderr = self._run(
            "local-batch",
            "--request",
            str(FIXTURE_ROOT / "newsletter_digest.json"),
            "--request",
            str(FIXTURE_ROOT / "bank_notice.json"),
            "--request",
            str(FIXTURE_ROOT / "unknown_message.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
            "--mark-read",
            "--record-approvable-intents",
            "--json",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["mode"], "local_batch")
        self.assertFalse(payload["gmail_mutation_enabled"])
        self.assertEqual(payload["review"]["summary"]["total_threads"], 3)
        self.assertEqual(payload["review"]["summary"]["review_required_count"], 2)
        self.assertEqual(payload["recorded_intent_count"], 1)
        self.assertEqual([item["preserve"]["status"] for item in payload["items"]], ["PRESERVED", "PRESERVED", "PRESERVED"])
        self.assertTrue(all(Path(item["preserve"]["package_path"]).is_dir() for item in payload["items"]))
        self.assertEqual(payload["items"][0]["review"]["category"], "newsletter")
        self.assertIsNotNone(payload["items"][0]["intent"])
        self.assertFalse(payload["items"][0]["intent"]["gmail_finalization"]["enabled"])
        self.assertTrue(payload["items"][0]["intent"]["gmail_finalization"]["mark_read"])
        self.assertIsNone(payload["items"][1]["intent"])
        self.assertIsNone(payload["items"][2]["intent"])

    def test_local_batch_without_intent_flag_preserves_and_reviews_only(self) -> None:
        exit_code, stdout, stderr = self._run(
            "local-batch",
            "--request",
            str(FIXTURE_ROOT / "newsletter_digest.json"),
            "--request",
            str(FIXTURE_ROOT / "automated_notice.json"),
            "--export-root",
            str(self.export_root),
            "--database-url",
            self.database_url,
            "--json",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["review"]["summary"]["review_required_count"], 0)
        self.assertEqual(payload["recorded_intent_count"], 0)
        self.assertTrue(all(item["intent"] is None for item in payload["items"]))
        self.assertEqual(
            payload["review"]["summary"]["by_gmail_action"],
            {
                "label_archive": 2,
            },
        )


if __name__ == "__main__":
    unittest.main()
