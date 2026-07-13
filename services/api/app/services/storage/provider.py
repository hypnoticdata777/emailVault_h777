from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.services.storage.paths import validate_trusted_relative_path


@dataclass(frozen=True)
class ArtifactToStore:
    """Generated archive artifact ready for storage staging.

    `trusted_name` must be server generated. Original email filenames are
    metadata only and must never be used as storage paths.
    """

    trusted_name: str
    source_path: Path
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class StageAndVerifyRequest:
    record_id: str
    artifacts: tuple[ArtifactToStore, ...]


@dataclass(frozen=True)
class StoredArtifact:
    trusted_name: str
    storage_path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class StageAndVerifyResult:
    verified: bool
    artifacts: tuple[StoredArtifact, ...]
    total_bytes: int


class StorageProvider(Protocol):
    def stage_and_verify(self, request: StageAndVerifyRequest) -> StageAndVerifyResult:
        raise NotImplementedError


class LocalFilesystemStorageProvider:
    """Local development storage provider with checksum verification.

    This class is deliberately limited to staging and verification. It does not
    update archive state, expose a completed record, or trigger Gmail
    finalization. Those decisions remain outside the storage boundary.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def stage_and_verify(self, request: StageAndVerifyRequest) -> StageAndVerifyResult:
        if not request.record_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Record identifier is required.", "record_id")
        if not request.artifacts:
            raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "At least one artifact is required.", "artifacts")

        record_dir = self.root / validate_trusted_relative_path(request.record_id)
        try:
            record_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Storage record path already exists.", "record_id") from exc

        stored: list[StoredArtifact] = []
        try:
            for artifact in request.artifacts:
                stored.append(self._copy_and_verify(record_dir, artifact))
        except Exception:
            shutil.rmtree(record_dir, ignore_errors=True)
            raise

        return StageAndVerifyResult(
            verified=True,
            artifacts=tuple(stored),
            total_bytes=sum(item.size_bytes for item in stored),
        )

    def _copy_and_verify(self, record_dir: Path, artifact: ArtifactToStore) -> StoredArtifact:
        trusted_name = validate_trusted_relative_path(artifact.trusted_name)
        if not artifact.source_path.is_file():
            raise ApiError(ErrorCategory.STORAGE_UNAVAILABLE, "Artifact source file does not exist.", "source_path")

        actual_size = artifact.source_path.stat().st_size
        if actual_size != artifact.size_bytes:
            raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Artifact size verification failed.", "size_bytes")

        destination = record_dir / trusted_name
        shutil.copyfile(artifact.source_path, destination)
        actual_hash = _sha256_file(destination)
        if actual_hash != artifact.sha256:
            raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Artifact checksum verification failed.", "sha256")

        return StoredArtifact(
            trusted_name=trusted_name,
            storage_path=str(Path(validate_trusted_relative_path(record_dir.name)) / trusted_name),
            sha256=actual_hash,
            size_bytes=actual_size,
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

