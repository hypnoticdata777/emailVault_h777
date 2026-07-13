from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from services.api.app.auth.identity import GoogleIdentity, GoogleOAuthIdentityVerifier, IdentityVerifier, StubIdentityVerifier
from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.repositories.interfaces import RevisionRepository
from services.api.app.repositories.sqlite import SqliteRevisionRepository, sqlite_path_from_database_url


def get_identity_verifier() -> IdentityVerifier:
    settings = load_settings()
    if settings.identity_verifier == "synthetic":
        return StubIdentityVerifier()
    if settings.identity_verifier == "google":
        return GoogleOAuthIdentityVerifier(settings.google_oauth_client_id)
    raise ApiError(
        ErrorCategory.AUTHENTICATION_AUTHORIZATION,
        "Identity verifier mode must be synthetic or google.",
        "EMAIL_VAULT_IDENTITY_VERIFIER",
    )


def get_revision_repository() -> RevisionRepository:
    settings = load_settings()
    return SqliteRevisionRepository(sqlite_path_from_database_url(settings.database_url))


@dataclass(frozen=True)
class RequestIdentity:
    google_identity: GoogleIdentity


async def require_identity(
    authorization: Annotated[str | None, Header()] = None,
    verifier: IdentityVerifier = Depends(get_identity_verifier),
) -> RequestIdentity:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "category": "authentication_authorization",
                "message": "A Google ID token bearer credential is required.",
            },
        )
    token = authorization.removeprefix("Bearer ").strip()
    identity = verifier.verify_id_token(token)
    return RequestIdentity(google_identity=identity)
