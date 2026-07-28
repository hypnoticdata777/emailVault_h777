from __future__ import annotations

import unittest

from services.api.app.auth.oauth_readiness import inspect_gmail_oauth_readiness
from services.api.app.core.settings import PLACEHOLDER_GOOGLE_CLIENT_ID, Settings


class GmailOAuthReadinessTests(unittest.TestCase):
    def test_readiness_reports_missing_client_id_and_secret(self) -> None:
        readiness = inspect_gmail_oauth_readiness(
            Settings(
                google_oauth_client_id=PLACEHOLDER_GOOGLE_CLIENT_ID,
                google_oauth_client_secret="",
            )
        )

        self.assertFalse(readiness.configured)
        self.assertIn("GOOGLE_OAUTH_CLIENT_ID", readiness.missing)
        self.assertIn("GOOGLE_OAUTH_CLIENT_SECRET", readiness.missing)
        self.assertFalse(readiness.client_id_configured)
        self.assertFalse(readiness.client_secret_configured)
        self.assertIsNone(readiness.authorization_url())

    def test_readiness_accepts_read_only_gmail_oauth_configuration(self) -> None:
        readiness = inspect_gmail_oauth_readiness(
            Settings(
                google_oauth_client_id="client-id.apps.googleusercontent.com",
                google_oauth_client_secret="client-secret",
                oauth_redirect_uri="http://127.0.0.1:8000/oauth/google/callback",
                gmail_oauth_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
            )
        )

        self.assertTrue(readiness.configured)
        self.assertEqual(readiness.missing, ())
        self.assertFalse(readiness.mutation_scopes_requested)
        authorization_url = readiness.authorization_url("state-123")
        self.assertIsNotNone(authorization_url)
        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth?", authorization_url)
        self.assertIn("client_id=client-id.apps.googleusercontent.com", authorization_url)
        self.assertIn("response_type=code", authorization_url)
        self.assertIn("access_type=offline", authorization_url)
        self.assertIn("state=state-123", authorization_url)

    def test_readiness_flags_mutation_capable_gmail_scopes(self) -> None:
        readiness = inspect_gmail_oauth_readiness(
            Settings(
                google_oauth_client_id="client-id.apps.googleusercontent.com",
                google_oauth_client_secret="client-secret",
                gmail_oauth_scopes=(
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.modify",
                ),
            )
        )

        self.assertTrue(readiness.configured)
        self.assertTrue(readiness.mutation_scopes_requested)


if __name__ == "__main__":
    unittest.main()
