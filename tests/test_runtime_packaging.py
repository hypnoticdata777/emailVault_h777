from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]


class RuntimePackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")

    def test_dockerfile_packages_api_runtime(self) -> None:
        self.assertIn("FROM python:3.12-slim", self.dockerfile)
        self.assertIn('python -m pip install --no-cache-dir ".[api,renderer]"', self.dockerfile)
        self.assertIn("python -m playwright install --with-deps chromium", self.dockerfile)
        self.assertIn("services.api.app.main:app", self.dockerfile)
        self.assertIn('"--host", "0.0.0.0"', self.dockerfile)
        self.assertIn('"--port", "8000"', self.dockerfile)

    def test_dockerfile_uses_non_root_user_and_healthcheck(self) -> None:
        self.assertIn("adduser --system --ingroup emailvault emailvault", self.dockerfile)
        self.assertIn("USER emailvault", self.dockerfile)
        self.assertIn("HEALTHCHECK", self.dockerfile)
        self.assertIn("http://127.0.0.1:8000/health", self.dockerfile)

    def test_dockerfile_uses_persistent_data_directory(self) -> None:
        self.assertIn("EMAIL_VAULT_STORAGE_ROOT=/data/email-vault-storage", self.dockerfile)
        self.assertIn("DATABASE_URL=sqlite:////data/email_vault.db", self.dockerfile)
        self.assertIn("mkdir -p /data/email-vault-storage", self.dockerfile)

    def test_dockerignore_excludes_local_secrets_and_non_runtime_files(self) -> None:
        required_ignores = {
            ".env",
            ".git/",
            ".local/",
            "email_vault.db",
            "tests/",
            "docs/",
            "services/gmail_addon/",
        }

        ignored = {line.strip() for line in self.dockerignore.splitlines() if line.strip()}
        self.assertTrue(required_ignores.issubset(ignored))


if __name__ == "__main__":
    unittest.main()
