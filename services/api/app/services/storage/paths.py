from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from services.api.app.domain.contracts import ApiError, ErrorCategory


def trusted_storage_name(identifier: UUID, extension: str) -> str:
    normalized_extension = extension.lower()
    if not normalized_extension.startswith("."):
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Stored extension must begin with a dot.", "extension")
    if any(char in normalized_extension for char in {"/", "\\", "\x00"}):
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Stored extension cannot contain path separators.", "extension")
    return f"{identifier}{normalized_extension}"


def validate_trusted_relative_path(path: str) -> str:
    if "\x00" in path:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Storage path cannot contain null bytes.", "storage_path")
    if PureWindowsPath(path).is_absolute() or PurePosixPath(path).is_absolute():
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Storage path must be relative.", "storage_path")
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if ".." in parts:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Storage path cannot traverse directories.", "storage_path")
    if len(parts) != 1:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Storage path must be a trusted generated filename.", "storage_path")
    return path

