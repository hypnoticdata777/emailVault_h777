from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services.api.app.domain.contracts import ApiError, ErrorCategory


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
