from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from services.api.app.auth.token_storage import (
    EncryptedLocalTokenStore,
    inspect_token_storage_readiness,
    stored_google_oauth_token,
)
from services.api.app.core.settings import Settings


HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None


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

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography is not installed")
    def test_encrypted_store_round_trips_without_plaintext_token_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "token-store.json"
            token = stored_google_oauth_token(
                owner_id="local-admin",
                access_token="access-token-secret",
                refresh_token="refresh-token-secret",
                token_type="Bearer",
                scopes=("https://www.googleapis.com/auth/gmail.readonly",),
                expires_in=3600,
                id_token="id-token-secret",
                now=1000,
            )

            store = EncryptedLocalTokenStore(path, "local-development-key")
            store.save(token)
            exists_after_save = store.exists()
            raw_file = path.read_text(encoding="utf-8")
            loaded = store.load()

        self.assertTrue(exists_after_save)
        self.assertNotIn("access-token-secret", raw_file)
        self.assertNotIn("refresh-token-secret", raw_file)
        self.assertEqual(loaded.access_token, "access-token-secret")
        self.assertEqual(loaded.refresh_token, "refresh-token-secret")
        self.assertEqual(loaded.expires_at, 4600)
        self.assertEqual(
            loaded.scopes,
            ("https://www.googleapis.com/auth/gmail.readonly",),
        )


if __name__ == "__main__":
    unittest.main()
