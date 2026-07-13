from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from services.api.app.api.dependencies import RequestIdentity, require_identity
from services.api.app.api.schemas import (
    ApiErrorSchema,
    ArchiveResultSchema,
    ArchiveStatusSchema,
    ArchiveThreadRequestSchema,
    GmailFinalizationInstructionsSchema,
)
from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import ApiError, ErrorCategory


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "email-vault-api"}


@router.post("/archive/thread", response_model=ArchiveResultSchema, status_code=status.HTTP_202_ACCEPTED)
async def archive_thread(
    payload: ArchiveThreadRequestSchema,
    identity: RequestIdentity = Depends(require_identity),
) -> ArchiveResultSchema:
    # P2 proves the HTTP boundary and contract validation only. The verified
    # Google identity is required now so later persistence cannot accidentally
    # trust a client-supplied owner id.
    del identity
    payload.to_domain().validate(load_settings())

    # Gmail finalization must stay disabled until a later phase has staged,
    # verified, and durably recorded the archive revision. Returning FAILED here
    # is intentional: it lets clients exercise the route without implying that a
    # partial archive is safe to label, mark read, or archive in Gmail.
    return ArchiveResultSchema(
        status=ArchiveStatusSchema.FAILED,
        gmail_finalization=GmailFinalizationInstructionsSchema(enabled=False),
        error=ApiErrorSchema(
            category=ErrorCategory.UNEXPECTED_INTERNAL.value,
            message="Archive execution is not implemented in P2. Gmail finalization is disabled.",
        ),
    )


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    del request
    # Keep controlled domain failures separate from unexpected framework errors
    # so API clients can make deterministic retry/finalization decisions.
    http_status = status.HTTP_400_BAD_REQUEST
    if exc.category == ErrorCategory.AUTHENTICATION_AUTHORIZATION:
        http_status = status.HTTP_401_UNAUTHORIZED
    elif exc.category in {
        ErrorCategory.STORAGE_UNAVAILABLE,
        ErrorCategory.STORAGE_VERIFICATION,
        ErrorCategory.UNEXPECTED_INTERNAL,
    }:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={"error": {"category": exc.category.value, "message": exc.message, "field": exc.field}},
    )
