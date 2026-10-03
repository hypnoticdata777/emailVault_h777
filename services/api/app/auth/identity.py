from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from services.api.app.domain.contracts import ApiError, ErrorCategory

PLACEHOLDER_GOOGLE_CLIENT_ID = "replace-with-google-oauth-client-id"


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    email_verified: bool


class IdentityVerifier(Protocol):
    """Boundary for replacing the P2 stub with real Google ID-token checks."""

    def verify_id_token(self, token: str) -> GoogleIdentity:
        raise NotImplementedError


class StubIdentityVerifier:
    """Synthetic verifier for local tests; never accepts real credentials."""

    def verify_id_token(self, token: str) -> GoogleIdentity:
        if token != "synthetic-valid-token":
            raise ApiError(ErrorCategory.AUTHENTICATION_AUTHORIZATION, "Google ID token could not be verified.")
        return GoogleIdentity(subject="google-subject-example", email="owner@example.com", email_verified=True)


class GoogleOAuthIdentityVerifier:
    """Verify Google ID tokens against the configured OAuth client id."""

    def __init__(
        self,
        client_id: str,
        verify_oauth2_token: Callable[[str, Any, str], dict[str, Any]] | None = None,
        request_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.client_id = client_id
        self._verify_oauth2_token = verify_oauth2_token
        self._request_factory = request_factory

    def verify_id_token(self, token: str) -> GoogleIdentity:
        if not token.strip():
            raise ApiError(ErrorCategory.AUTHENTICATION_AUTHORIZATION, "Google ID token is required.")
        if not self.client_id or self.client_id == PLACEHOLDER_GOOGLE_CLIENT_ID:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Google OAuth client id is not configured.",
                "GOOGLE_OAUTH_CLIENT_ID",
            )

        verifier = self._verify_oauth2_token or self._load_google_verifier()
        request = self._request_factory() if self._request_factory else self._load_google_request()
        try:
            claims = verifier(token, request, self.client_id)
        except ValueError as exc:
            raise ApiError(ErrorCategory.AUTHENTICATION_AUTHORIZATION, "Google ID token could not be verified.") from exc

        subject = str(claims.get("sub") or "")
        email = str(claims.get("email") or "")
        email_verified = _is_verified_email(claims.get("email_verified"))
        if not subject or not email:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Google ID token is missing required identity claims.",
            )

        return GoogleIdentity(subject=subject, email=email, email_verified=email_verified)

    @staticmethod
    def _load_google_verifier() -> Callable[[str, Any, str], dict[str, Any]]:
        try:
            from google.oauth2.id_token import verify_oauth2_token
        except ImportError as exc:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Google identity verification dependencies are not installed.",
            ) from exc
        return verify_oauth2_token

    @staticmethod
    def _load_google_request() -> Any:
        try:
            from google.auth.transport.requests import Request
        except ImportError as exc:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Google identity verification dependencies are not installed.",
            ) from exc
        return Request()


def _is_verified_email(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False
