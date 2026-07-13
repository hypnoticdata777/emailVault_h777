from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable
from uuid import UUID, uuid4

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference, ErrorCategory
from services.api.app.services.rendering.snapshot import RendererSafeThreadSnapshot
from services.api.app.services.storage.paths import trusted_storage_name, validate_trusted_relative_path


class PlannedArtifactKind(StrEnum):
    PDF = "pdf"
    METADATA_JSON = "metadata_json"
    MANIFEST_JSON = "manifest_json"


class PlannedArtifactStage(StrEnum):
    RENDERED = "rendered"
    METADATA = "metadata"
    MANIFEST = "manifest"


@dataclass(frozen=True)
class PlannedArtifact:
    kind: PlannedArtifactKind
    trusted_name: str
    content_type: str
    source_stage: PlannedArtifactStage
    required: bool = True


@dataclass(frozen=True)
class ArtifactManifestPlan:
    record_id: str
    vault_thread_id: str
    revision: int
    snapshot_sha256: str
    thread_id: str
    gmail_thread_id: str
    message_count: int
    blocked_remote_resources: int
    artifacts: tuple[PlannedArtifact, ...]


def plan_artifact_manifest(
    reference: ArchiveRecordReference,
    safe_thread: RendererSafeThreadSnapshot,
    uuid_factory: Callable[[], UUID] = uuid4,
) -> ArtifactManifestPlan:
    """Plan generated artifact names before rendering or storage writes occur."""

    _validate_reference(reference)
    if not safe_thread.messages:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Renderer-safe thread must include messages.", "thread.messages")

    return ArtifactManifestPlan(
        record_id=reference.record_id,
        vault_thread_id=reference.vault_thread_id,
        revision=reference.revision,
        snapshot_sha256=reference.snapshot_sha256,
        thread_id=safe_thread.thread_id,
        gmail_thread_id=safe_thread.gmail_thread_id,
        message_count=len(safe_thread.messages),
        blocked_remote_resources=safe_thread.blocked_remote_resources,
        artifacts=(
            _artifact(PlannedArtifactKind.PDF, ".pdf", "application/pdf", PlannedArtifactStage.RENDERED, uuid_factory),
            _artifact(
                PlannedArtifactKind.METADATA_JSON,
                ".metadata.json",
                "application/json",
                PlannedArtifactStage.METADATA,
                uuid_factory,
            ),
            _artifact(
                PlannedArtifactKind.MANIFEST_JSON,
                ".manifest.json",
                "application/json",
                PlannedArtifactStage.MANIFEST,
                uuid_factory,
            ),
        ),
    )


def _validate_reference(reference: ArchiveRecordReference) -> None:
    validate_trusted_relative_path(reference.record_id)
    if not reference.vault_thread_id:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Vault thread identifier is required.", "vault_thread_id")
    if reference.revision < 1:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Revision must be positive.", "revision")
    if not reference.snapshot_sha256:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Snapshot fingerprint is required.", "snapshot_sha256")


def _artifact(
    kind: PlannedArtifactKind,
    extension: str,
    content_type: str,
    source_stage: PlannedArtifactStage,
    uuid_factory: Callable[[], UUID],
) -> PlannedArtifact:
    return PlannedArtifact(
        kind=kind,
        trusted_name=trusted_storage_name(uuid_factory(), extension),
        content_type=content_type,
        source_stage=source_stage,
    )
