from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from services.api.app.api.dependencies import (
    RequestIdentity,
    get_attachment_content_provider,
    get_pdf_renderer_adapter,
    get_revision_repository,
    get_storage_provider,
    require_addon_request_signature,
    require_identity,
)
from services.api.app.api.schemas import (
    ApiErrorSchema,
    ArchiveResultSchema,
    ArchiveStatusSchema,
    ArchiveThreadRequestSchema,
    GmailFinalizationInstructionsSchema,
)
from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.repositories.interfaces import RevisionRepository
from services.api.app.services.archive import ArchiveCoordinator
from services.api.app.services.rendering.pdf import PdfRendererAdapter
from services.api.app.services.storage.attachments import AttachmentContentProvider
from services.api.app.services.storage.provider import StorageProvider


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "email-vault-api"}


@router.post(
    "/archive/thread",
    response_model=ArchiveResultSchema,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_addon_request_signature)],
)
async def archive_thread(
    payload: ArchiveThreadRequestSchema,
    identity: RequestIdentity = Depends(require_identity),
    repository: RevisionRepository = Depends(get_revision_repository),
    pdf_renderer: PdfRendererAdapter = Depends(get_pdf_renderer_adapter),
    storage_provider: StorageProvider = Depends(get_storage_provider),
    attachment_content_provider: AttachmentContentProvider = Depends(get_attachment_content_provider),
) -> ArchiveResultSchema:
    # Gmail mutation remains disabled here. The route may complete backend
    # preservation, but finalization instructions stay behind the explicit
    # post-completion boundary.
    result = ArchiveCoordinator(repository).preserve(
        payload.to_domain(),
        identity.google_identity,
        pdf_renderer,
        storage_provider,
        attachment_content_provider,
    )
    return ArchiveResultSchema.from_domain(result)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    del request
    # Keep controlled domain failures separate from unexpected framework errors
    # so API clients can make deterministic retry/finalization decisions.
    http_status = status.HTTP_400_BAD_REQUEST
    if exc.category == ErrorCategory.AUTHENTICATION_AUTHORIZATION:
        http_status = status.HTTP_401_UNAUTHORIZED
    elif exc.category in {
        ErrorCategory.SANITIZATION_RENDERING,
        ErrorCategory.STORAGE_UNAVAILABLE,
        ErrorCategory.STORAGE_VERIFICATION,
        ErrorCategory.UNEXPECTED_INTERNAL,
    }:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={"error": {"category": exc.category.value, "message": exc.message, "field": exc.field}},
    )
