from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Callable
from uuid import UUID, uuid4

from services.api.app.domain.contracts import (
    ApiError,
    ArchiveRecordReference,
    ErrorCategory,
    ThreadSnapshot,
)
from services.api.app.services.storage.paths import trusted_storage_name, validate_trusted_relative_path


EXPORT_PACKAGE_SCHEMA_VERSION = "email-vault.export-package.v1"


class ExportPackageMode(StrEnum):
    PRESERVE = "preserve"
    CLEAN_INBOX = "clean_inbox"
    FREE_SPACE = "free_space"


class ExportFolderLayout(StrEnum):
    DOMAIN_FIRST = "domain_first"
    CATEGORY_FIRST = "category_first"
    MIXED = "mixed"


class ExportCategory(StrEnum):
    NEWSLETTER = "newsletter"
    AUTOMATED = "automated"
    BANK_FINANCIAL = "bank_financial"
    HUMAN = "human"
    NEEDS_REVIEW = "needs_review"
    ATTACHMENTS_HEAVY = "attachments_heavy"
    UNKNOWN = "unknown"


class ExportArtifactKind(StrEnum):
    RAW_EML = "raw_eml"
    ATTACHMENT = "attachment"
    METADATA_JSON = "metadata_json"
    READABLE_HTML = "readable_html"
    READABLE_PDF = "readable_pdf"
    MANIFEST_JSON = "manifest_json"
    NORMALIZED_TEXT = "normalized_text"


@dataclass(frozen=True)
class ExportRoute:
    layout: ExportFolderLayout
    category: ExportCategory
    sender_domain: str
    relative_parts: tuple[str, ...]

    @property
    def relative_path(self) -> str:
        return "/".join(self.relative_parts)

    def validate(self) -> None:
        if not self.sender_domain or "." not in self.sender_domain:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Sender domain is required for export routing.", "sender_domain")
        validate_export_relative_parts(self.relative_parts)


@dataclass(frozen=True)
class ExportArtifactPlan:
    kind: ExportArtifactKind
    trusted_name: str
    content_type: str
    required: bool = True
    source_message_id: str | None = None
    source_attachment_id: str | None = None
    original_filename: str | None = None

    def validate(self) -> None:
        validate_trusted_relative_path(self.trusted_name)
        if not self.content_type:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Artifact content type is required.", "content_type")
        if self.kind == ExportArtifactKind.ATTACHMENT:
            if not self.source_message_id or not self.source_attachment_id:
                raise ApiError(
                    ErrorCategory.INVALID_SCHEMA,
                    "Attachment artifacts require source message and attachment identifiers.",
                    "artifact.source_attachment_id",
                )


@dataclass(frozen=True)
class ExportPackagePlan:
    schema_version: str
    record_id: str
    vault_thread_id: str
    revision: int
    snapshot_sha256: str
    gmail_thread_id: str
    mode: ExportPackageMode
    route: ExportRoute
    artifacts: tuple[ExportArtifactPlan, ...]

    @property
    def cleanup_allowed(self) -> bool:
        return self.mode in {ExportPackageMode.CLEAN_INBOX, ExportPackageMode.FREE_SPACE}

    def validate(self) -> None:
        if self.schema_version != EXPORT_PACKAGE_SCHEMA_VERSION:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Unsupported export package schema version.", "schema_version")
        validate_trusted_relative_path(self.record_id)
        if not self.vault_thread_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Vault thread identifier is required.", "vault_thread_id")
        if self.revision < 1:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Revision must be positive.", "revision")
        if not self.snapshot_sha256:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Snapshot fingerprint is required.", "snapshot_sha256")
        if not self.gmail_thread_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Gmail thread identifier is required.", "gmail_thread_id")
        self.route.validate()
        if not self.artifacts:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export package must include planned artifacts.", "artifacts")
        for artifact in self.artifacts:
            artifact.validate()


def plan_export_package(
    reference: ArchiveRecordReference,
    thread: ThreadSnapshot,
    route: ExportRoute,
    mode: ExportPackageMode = ExportPackageMode.PRESERVE,
    uuid_factory: Callable[[], UUID] = uuid4,
) -> ExportPackagePlan:
    artifacts = (
        _artifact(ExportArtifactKind.RAW_EML, ".eml", "message/rfc822", uuid_factory),
        _artifact(ExportArtifactKind.METADATA_JSON, ".metadata.json", "application/json", uuid_factory),
        _artifact(ExportArtifactKind.MANIFEST_JSON, ".manifest.json", "application/json", uuid_factory),
        _artifact(ExportArtifactKind.NORMALIZED_TEXT, ".txt", "text/plain", uuid_factory),
        _artifact(ExportArtifactKind.READABLE_HTML, ".html", "text/html", uuid_factory, required=False),
        _artifact(ExportArtifactKind.READABLE_PDF, ".pdf", "application/pdf", uuid_factory, required=False),
        *_attachment_artifacts(thread, uuid_factory),
    )
    plan = ExportPackagePlan(
        schema_version=EXPORT_PACKAGE_SCHEMA_VERSION,
        record_id=reference.record_id,
        vault_thread_id=reference.vault_thread_id,
        revision=reference.revision,
        snapshot_sha256=reference.snapshot_sha256,
        gmail_thread_id=thread.gmail_thread_id,
        mode=mode,
        route=route,
        artifacts=artifacts,
    )
    plan.validate()
    return plan


def domain_first_route(sender_domain: str, category: ExportCategory = ExportCategory.UNKNOWN) -> ExportRoute:
    safe_domain = normalize_route_segment(sender_domain)
    return ExportRoute(
        layout=ExportFolderLayout.DOMAIN_FIRST,
        category=category,
        sender_domain=safe_domain,
        relative_parts=(safe_domain,),
    )


def category_first_route(sender_domain: str, category: ExportCategory) -> ExportRoute:
    safe_domain = normalize_route_segment(sender_domain)
    safe_category = normalize_route_segment(category.value)
    return ExportRoute(
        layout=ExportFolderLayout.CATEGORY_FIRST,
        category=category,
        sender_domain=safe_domain,
        relative_parts=(safe_category, safe_domain),
    )


def normalize_route_segment(value: str) -> str:
    normalized = value.strip().lower().replace("\\", "-").replace("/", "-")
    normalized = "".join(char if char.isalnum() or char in {"-", ".", "_"} else "-" for char in normalized)
    normalized = "-".join(part for part in normalized.split("-") if part)
    if not normalized or normalized in {".", ".."}:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export route segment is required.", "export_route")
    return normalized


def validate_export_relative_parts(parts: tuple[str, ...]) -> None:
    if not parts:
        raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export route must include at least one folder.", "export_route")
    for part in parts:
        if "\x00" in part:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export route cannot contain null bytes.", "export_route")
        if not part or part in {".", ".."}:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export route contains an unsafe folder.", "export_route")
        if PureWindowsPath(part).is_absolute() or PurePosixPath(part).is_absolute():
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export route folders must be relative.", "export_route")
        if "/" in part or "\\" in part:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Export route folders cannot contain separators.", "export_route")


def _artifact(
    kind: ExportArtifactKind,
    extension: str,
    content_type: str,
    uuid_factory: Callable[[], UUID],
    required: bool = True,
    source_message_id: str | None = None,
    source_attachment_id: str | None = None,
    original_filename: str | None = None,
) -> ExportArtifactPlan:
    return ExportArtifactPlan(
        kind=kind,
        trusted_name=trusted_storage_name(uuid_factory(), extension),
        content_type=content_type,
        required=required,
        source_message_id=source_message_id,
        source_attachment_id=source_attachment_id,
        original_filename=original_filename,
    )


def _attachment_artifacts(
    thread: ThreadSnapshot,
    uuid_factory: Callable[[], UUID],
) -> tuple[ExportArtifactPlan, ...]:
    artifacts: list[ExportArtifactPlan] = []
    for message in thread.messages:
        for attachment in message.attachments:
            artifacts.append(
                _artifact(
                    ExportArtifactKind.ATTACHMENT,
                    attachment.extension,
                    attachment.mime_type,
                    uuid_factory,
                    source_message_id=message.message_id,
                    source_attachment_id=attachment.attachment_id,
                    original_filename=attachment.original_filename,
                )
            )
    return tuple(artifacts)
