from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePath
from typing import Any

from services.api.app.core.settings import Settings, load_settings


class ArchiveStatus(StrEnum):
    PRESERVED = "PRESERVED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class ArchiveState(StrEnum):
    REQUESTED = "REQUESTED"
    AUTHENTICATED = "AUTHENTICATED"
    VALIDATED = "VALIDATED"
    EXTRACTED = "EXTRACTED"
    SANITIZED = "SANITIZED"
    RENDERED = "RENDERED"
    STAGED = "STAGED"
    VERIFIED = "VERIFIED"
    GMAIL_FINALIZATION_PENDING = "GMAIL_FINALIZATION_PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PRESERVED_GMAIL_FINALIZATION_FAILED = "PRESERVED_GMAIL_FINALIZATION_FAILED"


class ErrorCategory(StrEnum):
    AUTHENTICATION_AUTHORIZATION = "authentication_authorization"
    INVALID_SCHEMA = "invalid_schema"
    PAYLOAD_ATTACHMENT_LIMIT = "payload_attachment_limit"
    UNSUPPORTED_ATTACHMENT = "unsupported_attachment"
    SANITIZATION_RENDERING = "sanitization_rendering"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    STORAGE_VERIFICATION = "storage_verification"
    DUPLICATE_CONFLICT = "duplicate_conflict_internal_consistency"
    GMAIL_FINALIZATION = "gmail_finalization"
    UNEXPECTED_INTERNAL = "unexpected_internal_error"


@dataclass(frozen=True)
class ApiError(Exception):
    category: ErrorCategory
    message: str
    field: str | None = None


@dataclass(frozen=True)
class Participant:
    email: str
    display_name: str | None = None

    def validate(self) -> None:
        if not self.email or "@" not in self.email:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Participant email is required.", "participant.email")


@dataclass(frozen=True)
class BodyRepresentation:
    mime_type: str
    content: str

    def validate(self) -> None:
        if self.mime_type not in {"text/plain", "text/html"}:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Body representation must be text/plain or text/html.", "body.mime_type")
        if self.content is None:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Body content is required.", "body.content")


@dataclass(frozen=True)
class AttachmentDescriptor:
    attachment_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    content_sha256: str | None = None

    @property
    def extension(self) -> str:
        suffix = PurePath(self.original_filename).suffix.lower()
        return suffix

    def validate(self, settings: Settings) -> None:
        if not self.attachment_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Attachment identifier is required.", "attachment.attachment_id")
        if not self.original_filename:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Original filename is required as metadata.", "attachment.original_filename")
        if self.size_bytes < 0:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Attachment size cannot be negative.", "attachment.size_bytes")
        if self.size_bytes > settings.max_attachment_bytes:
            raise ApiError(ErrorCategory.PAYLOAD_ATTACHMENT_LIMIT, "Attachment exceeds individual size limit.", "attachment.size_bytes")
        if self.mime_type not in settings.allowed_mime_types or self.extension not in settings.allowed_extensions:
            raise ApiError(ErrorCategory.UNSUPPORTED_ATTACHMENT, "Attachment type is not allowlisted.", "attachment.mime_type")


@dataclass(frozen=True)
class MessageSnapshot:
    message_id: str
    gmail_message_id: str
    sent_at: datetime
    from_participant: Participant
    to: tuple[Participant, ...]
    cc: tuple[Participant, ...] = ()
    bcc: tuple[Participant, ...] = ()
    labels: tuple[str, ...] = ()
    is_read: bool = False
    bodies: tuple[BodyRepresentation, ...] = ()
    attachments: tuple[AttachmentDescriptor, ...] = ()

    def validate(self, settings: Settings) -> None:
        if not self.message_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Message identifier is required.", "messages.message_id")
        if not self.gmail_message_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Gmail message identifier is required.", "messages.gmail_message_id")
        self.from_participant.validate()
        for participant in self.to + self.cc + self.bcc:
            participant.validate()
        if not self.bodies:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "At least one body representation is required.", "messages.bodies")
        for body in self.bodies:
            body.validate()
        for attachment in self.attachments:
            attachment.validate(settings)


@dataclass(frozen=True)
class ThreadSnapshot:
    thread_id: str
    gmail_thread_id: str
    subject: str
    messages: tuple[MessageSnapshot, ...]
    date_range_start: datetime
    date_range_end: datetime

    def validate(self, settings: Settings) -> None:
        if not self.thread_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Thread identifier is required.", "thread.thread_id")
        if not self.gmail_thread_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Gmail thread identifier is required.", "thread.gmail_thread_id")
        if not self.messages:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "At least one message is required.", "thread.messages")
        attachment_count = 0
        total_bytes = 0
        for message in self.messages:
            message.validate(settings)
            attachment_count += len(message.attachments)
            total_bytes += sum(attachment.size_bytes for attachment in message.attachments)
        if attachment_count > settings.max_attachments:
            raise ApiError(ErrorCategory.PAYLOAD_ATTACHMENT_LIMIT, "Attachment count exceeds configured limit.", "thread.attachments")
        if total_bytes > settings.max_total_payload_bytes:
            raise ApiError(ErrorCategory.PAYLOAD_ATTACHMENT_LIMIT, "Total attachment payload exceeds configured limit.", "thread.attachments")


@dataclass(frozen=True)
class ArchivePreferences:
    category: str
    mark_read_after_preserve: bool = False
    archive_after_preserve: bool = False


@dataclass(frozen=True)
class ClientContext:
    add_on_version: str
    locale: str = "en-US"
    timezone: str = "UTC"


@dataclass(frozen=True)
class ArchiveThreadRequest:
    request_id: str
    client_context: ClientContext
    preferences: ArchivePreferences
    thread: ThreadSnapshot
    confirmed_at: datetime

    def validate(self, settings: Settings | None = None) -> None:
        active_settings = settings or load_settings()
        if not self.request_id:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Request identifier is required.", "request_id")
        self.thread.validate(active_settings)


@dataclass(frozen=True)
class ArchiveRecordReference:
    vault_thread_id: str
    revision: int
    record_id: str
    snapshot_sha256: str


@dataclass(frozen=True)
class VerificationSummary:
    verified: bool
    artifact_count: int
    total_bytes: int
    verified_at: datetime | None = None


@dataclass(frozen=True)
class GmailFinalizationInstructions:
    apply_label: str = "EmailVault/Vaulted"
    mark_read: bool = False
    archive: bool = False
    enabled: bool = False


@dataclass(frozen=True)
class ArchiveResult:
    status: ArchiveStatus
    record: ArchiveRecordReference | None = None
    verification: VerificationSummary | None = None
    gmail_finalization: GmailFinalizationInstructions = field(default_factory=GmailFinalizationInstructions)
    error: ApiError | None = None


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
        return normalized.isoformat()
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    return value


def canonical_json(value: Any) -> str:
    raw = asdict(value) if hasattr(value, "__dataclass_fields__") else value
    return json.dumps(_normalize(raw), sort_keys=True, separators=(",", ":"))


def snapshot_fingerprint(thread: ThreadSnapshot) -> str:
    return hashlib.sha256(canonical_json(thread).encode("utf-8")).hexdigest()

