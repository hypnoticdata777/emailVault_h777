from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from services.api.app.auth.identity import GoogleIdentity, IdentityVerifier, StubIdentityVerifier
from services.api.app.repositories.interfaces import RevisionRepository
from services.api.app.repositories.null import NullRevisionRepository


def get_identity_verifier() -> IdentityVerifier:
    return StubIdentityVerifier()


def get_revision_repository() -> RevisionRepository:
    return NullRevisionRepository()


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
