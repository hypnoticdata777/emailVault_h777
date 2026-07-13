from __future__ import annotations

from services.api.app.auth.identity import GoogleIdentity
from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import (
    ApiError,
    ArchiveResult,
    ArchiveStatus,
    ErrorCategory,
    GmailFinalizationInstructions,
)
from services.api.app.domain.contracts import ArchiveThreadRequest
from services.api.app.repositories.interfaces import RevisionRepository
from services.api.app.services.revision_planner import RevisionPlanner, RevisionPlanStatus


class ArchiveCoordinator:
    """Coordinates the P2 archive decision without performing preservation.

    Later phases will add sanitizer, renderer, storage verification, and durable
    state writes here. For now, the coordinator proves the ordering: authenticate,
    validate, fingerprint, check duplicate, and keep Gmail finalization disabled.
    """

    def __init__(self, repository: RevisionRepository) -> None:
        self.repository = repository

    def evaluate(self, request: ArchiveThreadRequest, identity: GoogleIdentity) -> ArchiveResult:
        if not identity.email_verified:
            raise ApiError(
                ErrorCategory.AUTHENTICATION_AUTHORIZATION,
                "Verified Google email is required.",
                "identity.email_verified",
            )

        request.validate(load_settings())
        plan = RevisionPlanner(self.repository).plan(identity.subject, request.thread)
        if plan.status == RevisionPlanStatus.DUPLICATE:
            return ArchiveResult(
                status=ArchiveStatus.DUPLICATE,
                record=plan.reference,
                gmail_finalization=GmailFinalizationInstructions(enabled=False),
            )

        return ArchiveResult(
            status=ArchiveStatus.FAILED,
            gmail_finalization=GmailFinalizationInstructions(enabled=False),
            error=ApiError(
                ErrorCategory.UNEXPECTED_INTERNAL,
                "Archive execution is not implemented in P2. Gmail finalization is disabled.",
            ),
        )
