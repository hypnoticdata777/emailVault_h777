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
    GmailFinalizationCallbackRequestSchema,
    GmailFinalizationCallbackResultSchema,
    GmailFinalizationInstructionsSchema,
    GmailFinalizationRequestResultSchema,
    GmailFinalizationRequestSchema,
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
    trusted_attachment_provider = payload.attachment_content_provider(attachment_content_provider)
    result = ArchiveCoordinator(repository).preserve(
        payload.to_domain(),
        identity.google_identity,
        pdf_renderer,
        storage_provider,
        trusted_attachment_provider,
    )
    return ArchiveResultSchema.from_domain(result)


@router.post(
    "/archive/thread/gmail-finalization",
    response_model=GmailFinalizationRequestResultSchema,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_addon_request_signature)],
)
async def request_gmail_finalization(
    payload: GmailFinalizationRequestSchema,
    identity: RequestIdentity = Depends(require_identity),
    repository: RevisionRepository = Depends(get_revision_repository),
) -> GmailFinalizationRequestResultSchema:
    # This route is the explicit handoff from completed backend preservation to
    # Gmail-side follow-up. The archive route stays mutation-free by design.
    outcome = ArchiveCoordinator(repository).request_gmail_finalization(
        identity.google_identity,
        payload.record_id,
        payload.preferences.to_domain(),
    )
    return GmailFinalizationRequestResultSchema.from_domain(outcome)


@router.post(
    "/archive/thread/gmail-finalization/callback",
    response_model=GmailFinalizationCallbackResultSchema,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_addon_request_signature)],
)
async def record_gmail_finalization_callback(
    payload: GmailFinalizationCallbackRequestSchema,
    identity: RequestIdentity = Depends(require_identity),
    repository: RevisionRepository = Depends(get_revision_repository),
) -> GmailFinalizationCallbackResultSchema:
    # The add-on reports only the final Gmail-side outcome; state transition
    # policy rejects callbacks that do not follow a pending finalization request.
    outcome = ArchiveCoordinator(repository).record_gmail_finalization_callback(
        identity.google_identity,
        payload.record_id,
        payload.succeeded,
    )
    return GmailFinalizationCallbackResultSchema.from_domain(outcome)


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
