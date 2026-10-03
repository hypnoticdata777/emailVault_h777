from __future__ import annotations

import importlib.util
import os
import unittest
from unittest.mock import patch

from services.api.app.auth.identity import (
    GoogleOAuthIdentityVerifier,
    PLACEHOLDER_GOOGLE_CLIENT_ID,
    StubIdentityVerifier,
)
from services.api.app.domain.contracts import ApiError, ErrorCategory


HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None


class GoogleOAuthIdentityVerifierTests(unittest.TestCase):
    def test_google_verifier_accepts_verified_claims(self) -> None:
        request = object()
        calls: list[tuple[str, object, str]] = []

        def fake_verify(token: str, transport_request: object, client_id: str) -> dict[str, object]:
            calls.append((token, transport_request, client_id))
            return {"sub": "google-subject-real", "email": "owner@example.com", "email_verified": True}

        verifier = GoogleOAuthIdentityVerifier(
            "client.apps.googleusercontent.com",
            verify_oauth2_token=fake_verify,
            request_factory=lambda: request,
        )

        identity = verifier.verify_id_token("signed-google-id-token")

        self.assertEqual(identity.subject, "google-subject-real")
        self.assertEqual(identity.email, "owner@example.com")
        self.assertTrue(identity.email_verified)
        self.assertEqual(calls, [("signed-google-id-token", request, "client.apps.googleusercontent.com")])

    def test_google_verifier_accepts_string_true_email_verified_claim(self) -> None:
        verifier = GoogleOAuthIdentityVerifier(
            "client.apps.googleusercontent.com",
            verify_oauth2_token=lambda _token, _request, _client_id: {
                "sub": "google-subject-real",
                "email": "owner@example.com",
                "email_verified": "true",
            },
            request_factory=object,
        )

        identity = verifier.verify_id_token("signed-google-id-token")

        self.assertTrue(identity.email_verified)

    def test_google_verifier_rejects_placeholder_client_id_before_google_call(self) -> None:
        called = False

        def fake_verify(_token: str, _request: object, _client_id: str) -> dict[str, object]:
            nonlocal called
            called = True
            return {}

        verifier = GoogleOAuthIdentityVerifier(
            PLACEHOLDER_GOOGLE_CLIENT_ID,
            verify_oauth2_token=fake_verify,
            request_factory=object,
        )

        with self.assertRaises(ApiError) as context:
            verifier.verify_id_token("signed-google-id-token")

        self.assertFalse(called)
        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION_AUTHORIZATION)
        self.assertEqual(context.exception.field, "GOOGLE_OAUTH_CLIENT_ID")

    def test_google_verifier_maps_google_value_error_to_controlled_error(self) -> None:
        def fake_verify(_token: str, _request: object, _client_id: str) -> dict[str, object]:
            raise ValueError("bad token")

        verifier = GoogleOAuthIdentityVerifier(
            "client.apps.googleusercontent.com",
            verify_oauth2_token=fake_verify,
            request_factory=object,
        )

        with self.assertRaises(ApiError) as context:
            verifier.verify_id_token("signed-google-id-token")

        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION_AUTHORIZATION)
        self.assertEqual(context.exception.message, "Google ID token could not be verified.")

    def test_google_verifier_rejects_missing_required_identity_claims(self) -> None:
        verifier = GoogleOAuthIdentityVerifier(
            "client.apps.googleusercontent.com",
            verify_oauth2_token=lambda _token, _request, _client_id: {"email": "owner@example.com"},
            request_factory=object,
        )

        with self.assertRaises(ApiError) as context:
            verifier.verify_id_token("signed-google-id-token")

        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION_AUTHORIZATION)
        self.assertEqual(context.exception.message, "Google ID token is missing required identity claims.")


@unittest.skipUnless(HAS_FASTAPI, "FastAPI is not installed")
class IdentityDependencyTests(unittest.TestCase):
    def test_dependency_defaults_to_synthetic_identity_verifier(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            from services.api.app.api.dependencies import get_identity_verifier

            self.assertIsInstance(get_identity_verifier(), StubIdentityVerifier)

    def test_dependency_selects_google_identity_verifier(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EMAIL_VAULT_IDENTITY_VERIFIER": "google",
                "GOOGLE_OAUTH_CLIENT_ID": "client.apps.googleusercontent.com",
            },
            clear=True,
        ):
            from services.api.app.api.dependencies import get_identity_verifier

            self.assertIsInstance(get_identity_verifier(), GoogleOAuthIdentityVerifier)

    def test_dependency_rejects_unknown_identity_verifier_mode(self) -> None:
        with patch.dict(os.environ, {"EMAIL_VAULT_IDENTITY_VERIFIER": "mystery"}, clear=True):
            from services.api.app.api.dependencies import get_identity_verifier

            with self.assertRaises(ApiError) as context:
                get_identity_verifier()

        self.assertEqual(context.exception.category, ErrorCategory.AUTHENTICATION_AUTHORIZATION)
        self.assertEqual(context.exception.field, "EMAIL_VAULT_IDENTITY_VERIFIER")


if __name__ == "__main__":
    unittest.main()
