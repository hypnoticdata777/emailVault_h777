from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable

from services.api.app.domain.contracts import ApiError, ErrorCategory


SIGNATURE_VERSION = "v1"


def canonical_request(method: str, path: str, timestamp: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    return "\n".join((SIGNATURE_VERSION, method.upper(), path, timestamp, body_hash))


def sign_request(secret: str, method: str, path: str, timestamp: str, body: bytes) -> str:
    canonical = canonical_request(method, path, timestamp, body)
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


class AddonRequestSignatureVerifier:
    """Optional HMAC boundary for Workspace Add-on calls into the backend."""

    def __init__(
        self,
        secret: str | None,
        max_age_seconds: int = 300,
        now_factory: Callable[[], float] | None = None,
    ) -> None:
        # Coerce None to empty string and strip once to avoid AttributeError on None.
        self.secret = (secret or "").strip()
        self.max_age_seconds = max_age_seconds
        self._now_factory = now_factory or time.time

    @property
    def enabled(self) -> bool:
        # True only when a non-empty secret is configured.
        return bool(self.secret)

    def verify(self, method: str, path: str, body: bytes, timestamp: str | None, signature: str | None) -> None:
        if not self.enabled:
            return
        if not timestamp or not signature:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Signed add-on request headers are required.",
            )

        try:
            requested_at = int(timestamp)
        except ValueError as exc:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Signed add-on request timestamp is invalid.",
                "X-Email-Vault-Timestamp",
            ) from exc

        now = int(self._now_factory())
        if abs(now - requested_at) > self.max_age_seconds:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Signed add-on request timestamp is outside the allowed window.",
                "X-Email-Vault-Timestamp",
            )

        expected = sign_request(self.secret, method, path, timestamp, body)
        if not hmac.compare_digest(expected, signature):
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Signed add-on request signature could not be verified.",
                "X-Email-Vault-Signature",
            )
