from __future__ import annotations

import unittest

from services.api.app.auth.oauth_exchange import OAuthExchangeError, OAuthTokenSet


class OAuthExchangeTests(unittest.TestCase):
    def test_google_token_response_becomes_private_token_set(self) -> None:
        token_set = OAuthTokenSet.from_google_response(
            {
                "access_token": "access-token-secret",
                "refresh_token": "refresh-token-secret",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/gmail.readonly",
                "id_token": "id-token-secret",
            },
            ("https://www.googleapis.com/auth/gmail.readonly",),
            now=1000,
        )

        self.assertEqual(token_set.access_token, "access-token-secret")
        self.assertEqual(token_set.refresh_token, "refresh-token-secret")
        self.assertEqual(token_set.token_type, "Bearer")
        self.assertEqual(token_set.expires_in, 3600)
        self.assertEqual(token_set.scopes, ("https://www.googleapis.com/auth/gmail.readonly",))
        self.assertEqual(token_set.received_at, 1000)

    def test_google_token_response_requires_access_token(self) -> None:
        with self.assertRaises(OAuthExchangeError):
            OAuthTokenSet.from_google_response(
                {"token_type": "Bearer"},
                ("https://www.googleapis.com/auth/gmail.readonly",),
            )


if __name__ == "__main__":
    unittest.main()
