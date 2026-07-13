from __future__ import annotations

from services.api.app.domain.contracts import ApiError, ArchiveState, ErrorCategory


ALLOWED_TRANSITIONS: dict[ArchiveState, frozenset[ArchiveState]] = {
    ArchiveState.REQUESTED: frozenset({ArchiveState.AUTHENTICATED, ArchiveState.FAILED}),
    ArchiveState.AUTHENTICATED: frozenset({ArchiveState.VALIDATED, ArchiveState.FAILED}),
    ArchiveState.VALIDATED: frozenset({ArchiveState.EXTRACTED, ArchiveState.FAILED}),
    ArchiveState.EXTRACTED: frozenset({ArchiveState.SANITIZED, ArchiveState.FAILED}),
    ArchiveState.SANITIZED: frozenset({ArchiveState.RENDERED, ArchiveState.FAILED}),
    ArchiveState.RENDERED: frozenset({ArchiveState.STAGED, ArchiveState.FAILED}),
    ArchiveState.STAGED: frozenset({ArchiveState.VERIFIED, ArchiveState.FAILED}),
    ArchiveState.VERIFIED: frozenset({ArchiveState.GMAIL_FINALIZATION_PENDING, ArchiveState.COMPLETED}),
    ArchiveState.GMAIL_FINALIZATION_PENDING: frozenset(
        {ArchiveState.COMPLETED, ArchiveState.PRESERVED_GMAIL_FINALIZATION_FAILED}
    ),
    ArchiveState.COMPLETED: frozenset(),
    ArchiveState.FAILED: frozenset(),
    ArchiveState.PRESERVED_GMAIL_FINALIZATION_FAILED: frozenset(),
}


def assert_transition_allowed(current: ArchiveState, target: ArchiveState) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ApiError(
            ErrorCategory.GMAIL_FINALIZATION
            if target == ArchiveState.GMAIL_FINALIZATION_PENDING
            else ErrorCategory.DUPLICATE_CONFLICT,
            f"Invalid state transition from {current} to {target}.",
            "archive_state",
        )

