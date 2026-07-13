from __future__ import annotations

import tempfile
from pathlib import Path

from services.api.app.services.rendering.pdf import RenderedPdfArtifact
from services.api.app.services.storage.provider import (
    ArtifactToStore,
    StageAndVerifyRequest,
    StageAndVerifyResult,
    StorageProvider,
)


def stage_and_verify_rendered_pdf(
    record_id: str,
    rendered_pdf: RenderedPdfArtifact,
    storage_provider: StorageProvider,
    temp_root: Path | None = None,
) -> StageAndVerifyResult:
    """Stage a rendered PDF without recording completion or Gmail finalization."""

    with tempfile.TemporaryDirectory(prefix="email-vault-stage-", dir=temp_root) as workspace:
        source_path = Path(workspace) / rendered_pdf.trusted_name
        source_path.write_bytes(rendered_pdf.content)
        artifact = ArtifactToStore(
            trusted_name=rendered_pdf.trusted_name,
            source_path=source_path,
            sha256=rendered_pdf.sha256,
            size_bytes=rendered_pdf.size_bytes,
        )
        return storage_provider.stage_and_verify(StageAndVerifyRequest(record_id=record_id, artifacts=(artifact,)))
