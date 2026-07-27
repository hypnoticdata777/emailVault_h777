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


if __name__ == "__main__":
    unittest.main()
