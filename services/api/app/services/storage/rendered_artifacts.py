from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

from services.api.app.services.rendering.pdf import RenderedPdfArtifact
from services.api.app.services.storage.provider import (
    ArtifactToStore,
    StageAndVerifyRequest,
    StageAndVerifyResult,
    StorageProvider,
)


class GeneratedArtifact(Protocol):
    trusted_name: str
    content_type: str
    content: bytes
    sha256: str
    size_bytes: int


def stage_and_verify_rendered_pdf(
    record_id: str,
    rendered_pdf: RenderedPdfArtifact,
    storage_provider: StorageProvider,
    temp_root: Path | None = None,
) -> StageAndVerifyResult:
    """Stage a rendered PDF without recording completion or Gmail finalization."""

    return stage_and_verify_generated_artifacts(record_id, (rendered_pdf,), storage_provider, temp_root=temp_root)


def stage_and_verify_generated_artifacts(
    record_id: str,
    artifacts: tuple[GeneratedArtifact, ...],
    storage_provider: StorageProvider,
    temp_root: Path | None = None,
) -> StageAndVerifyResult:
    """Stage generated archive artifacts without recording archive state."""

    with tempfile.TemporaryDirectory(prefix="email-vault-stage-", dir=temp_root) as workspace:
        staged_artifacts: list[ArtifactToStore] = []
        for artifact in artifacts:
            source_path = Path(workspace) / artifact.trusted_name
            source_path.write_bytes(artifact.content)
            staged_artifacts.append(
                ArtifactToStore(
                    trusted_name=artifact.trusted_name,
                    source_path=source_path,
                    sha256=artifact.sha256,
                    size_bytes=artifact.size_bytes,
                )
            )
        return storage_provider.stage_and_verify(
            StageAndVerifyRequest(record_id=record_id, artifacts=tuple(staged_artifacts))
        )
