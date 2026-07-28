from __future__ import annotations

import unittest
from pathlib import Path

from services.api.app.auth.token_storage import inspect_token_storage_readiness
from services.api.app.core.settings import Settings


class TokenStorageReadinessTests(unittest.TestCase):
    def test_token_storage_readiness_requires_encryption_key(self) -> None:
        readiness = inspect_token_storage_readiness(
            Settings(
                token_store_path=Path(".local/email-vault-token-store.json"),
                token_encryption_key="",
            )
        )

        self.assertFalse(readiness.configured)
        self.assertIn("EMAIL_VAULT_TOKEN_ENCRYPTION_KEY", readiness.missing)
        self.assertFalse(readiness.encryption_key_configured)
        self.assertFalse(readiness.stores_plaintext_tokens)

    def test_token_storage_readiness_accepts_private_key_and_path(self) -> None:
        readiness = inspect_token_storage_readiness(
            Settings(
                token_store_path=Path(".local/email-vault-token-store.json"),
                token_encryption_key="local-development-key",
            )
        )

        self.assertTrue(readiness.configured)
        self.assertEqual(readiness.missing, ())
        self.assertTrue(readiness.encryption_key_configured)
        self.assertIn("email-vault-token-store.json", readiness.token_store_path)
        self.assertFalse(readiness.stores_plaintext_tokens)


if __name__ == "__main__":
    unittest.main()
