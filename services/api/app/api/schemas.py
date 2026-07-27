from __future__ import annotations

import base64
import binascii
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import (
    ApiError,
    ArchivePreferences,
    ArchiveRecordReference,
    ArchiveResult,
    ArchiveState,
    ArchiveStatus,
    ArchiveThreadRequest,
    AttachmentDescriptor,
    BodyRepresentation,
    ClientContext,
    ErrorCategory,
    GmailFinalizationInstructions,
    MessageHeader,
    MessageSnapshot,
    Participant,
    ThreadSnapshot,
    VerificationSummary,
)
from services.api.app.services.storage.attachments import AttachmentContentProvider, MappingAttachmentContentProvider


class ArchiveStatusSchema(StrEnum):
    PRESERVED = "PRESERVED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class ParticipantSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def email_must_be_present(cls, value: str) -> str:
        if not value or "@" not in value:
            raise ValueError("participant email is required")
        return value

    def to_domain(self) -> Participant:
        return Participant(email=self.email, display_name=self.display_name)


class BodyRepresentationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mime_type: str
    content: str

    @field_validator("mime_type")
    @classmethod
    def body_mime_type_must_be_supported(cls, value: str) -> str:
        if value not in {"text/plain", "text/html"}:
            raise ValueError("body representation must be text/plain or text/html")
        return value

    def to_domain(self) -> BodyRepresentation:
        return BodyRepresentation(mime_type=self.mime_type, content=self.content)


class MessageHeaderSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str

    @field_validator("name")
    @classmethod
    def header_name_must_be_present(cls, value: str) -> str:
        if not value:
            raise ValueError("header name is required")
        return value

    def to_domain(self) -> MessageHeader:
        return MessageHeader(name=self.name, value=self.value)


class AttachmentDescriptorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attachment_id: str
    original_filename: str
    mime_type: str
    size_bytes: int = Field(ge=0)
    content_sha256: str | None = None
    trusted_content_base64: str | None = None

    @model_validator(mode="after")
    def trusted_content_requires_checksum(self) -> "AttachmentDescriptorSchema":
        if self.trusted_content_base64 is not None:
            if not self.content_sha256:
                raise ValueError("trusted attachment content requires content_sha256")
            if len(self.content_sha256) != 64:
                raise ValueError("trusted attachment content requires a 64 character SHA-256")
        return self

    def to_domain(self) -> AttachmentDescriptor:
        return AttachmentDescriptor(
            attachment_id=self.attachment_id,
            original_filename=self.original_filename,
            mime_type=self.mime_type,
            size_bytes=self.size_bytes,
            content_sha256=self.content_sha256,
        )

    def trusted_content_bytes(self) -> bytes | None:
        if self.trusted_content_base64 is None:
            return None
        try:
            return base64.b64decode(self.trusted_content_base64, validate=True)
        except binascii.Error as exc:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Trusted attachment content must be valid base64.", "attachment.trusted_content_base64") from exc


class MessageSnapshotSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    message_id: str
    gmail_message_id: str
    sent_at: datetime
    from_participant: ParticipantSchema = Field(alias="from")
    to: tuple[ParticipantSchema, ...]
    cc: tuple[ParticipantSchema, ...] = ()
    bcc: tuple[ParticipantSchema, ...] = ()
    labels: tuple[str, ...] = ()
    is_read: bool = False
    headers: tuple[MessageHeaderSchema, ...] = ()
    bodies: tuple[BodyRepresentationSchema, ...]
    attachments: tuple[AttachmentDescriptorSchema, ...] = ()

    @model_validator(mode="after")
    def required_message_fields(self) -> "MessageSnapshotSchema":
        if not self.message_id:
            raise ValueError("message identifier is required")
        if not self.gmail_message_id:
            raise ValueError("gmail message identifier is required")
        if not self.bodies:
            raise ValueError("at least one body representation is required")
        return self

    def to_domain(self) -> MessageSnapshot:
        return MessageSnapshot(
            message_id=self.message_id,
            gmail_message_id=self.gmail_message_id,
            sent_at=self.sent_at,
            from_participant=self.from_participant.to_domain(),
            to=tuple(item.to_domain() for item in self.to),
            cc=tuple(item.to_domain() for item in self.cc),
            bcc=tuple(item.to_domain() for item in self.bcc),
            labels=self.labels,
            is_read=self.is_read,
            headers=tuple(item.to_domain() for item in self.headers),
            bodies=tuple(item.to_domain() for item in self.bodies),
            attachments=tuple(item.to_domain() for item in self.attachments),
        )


class ThreadSnapshotSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    gmail_thread_id: str
    subject: str
    messages: tuple[MessageSnapshotSchema, ...]
    date_range_start: datetime
    date_range_end: datetime

    @model_validator(mode="after")
    def validate_thread_limits(self) -> "ThreadSnapshotSchema":
        if not self.thread_id:
            raise ValueError("thread identifier is required")
        if not self.gmail_thread_id:
            raise ValueError("gmail thread identifier is required")
        if not self.messages:
            raise ValueError("at least one message is required")
        settings = load_settings()
        attachments = [attachment for message in self.messages for attachment in message.attachments]
        if len(attachments) > settings.max_attachments:
            raise ValueError("attachment count exceeds configured limit")
        if sum(attachment.size_bytes for attachment in attachments) > settings.max_total_payload_bytes:
            raise ValueError("total attachment payload exceeds configured limit")
        return self

    def to_domain(self) -> ThreadSnapshot:
        return ThreadSnapshot(
            thread_id=self.thread_id,
            gmail_thread_id=self.gmail_thread_id,
            subject=self.subject,
            messages=tuple(item.to_domain() for item in self.messages),
            date_range_start=self.date_range_start,
            date_range_end=self.date_range_end,
        )


class ArchivePreferencesSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    mark_read_after_preserve: bool = False
    archive_after_preserve: bool = False

    def to_domain(self) -> ArchivePreferences:
        return ArchivePreferences(
            category=self.category,
            mark_read_after_preserve=self.mark_read_after_preserve,
            archive_after_preserve=self.archive_after_preserve,
        )


class ClientContextSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    add_on_version: str
    locale: str = "en-US"
    timezone: str = "UTC"

    def to_domain(self) -> ClientContext:
        return ClientContext(add_on_version=self.add_on_version, locale=self.locale, timezone=self.timezone)


class ArchiveThreadRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    client_context: ClientContextSchema
    preferences: ArchivePreferencesSchema
    thread: ThreadSnapshotSchema
    confirmed_at: datetime

    def to_domain(self) -> ArchiveThreadRequest:
        return ArchiveThreadRequest(
            request_id=self.request_id,
            client_context=self.client_context.to_domain(),
            preferences=self.preferences.to_domain(),
            thread=self.thread.to_domain(),
            confirmed_at=self.confirmed_at,
        )

    def attachment_content_provider(self, fallback: AttachmentContentProvider) -> AttachmentContentProvider:
        content_by_source: dict[tuple[str, str], bytes] = {}
        for message in self.thread.messages:
            for attachment in message.attachments:
                content = attachment.trusted_content_bytes()
                if content is not None:
                    content_by_source[(message.message_id, attachment.attachment_id)] = content
        if not content_by_source:
            return fallback
        return MappingAttachmentContentProvider(content_by_source, fallback)


class ApiErrorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    message: str
    field: str | None = None


class ArchiveRecordReferenceSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vault_thread_id: str
    revision: int
    record_id: str
    snapshot_sha256: str

    @classmethod
    def from_domain(cls, value: ArchiveRecordReference) -> "ArchiveRecordReferenceSchema":
        return cls(**value.__dict__)


class VerificationSummarySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: bool
    artifact_count: int
    total_bytes: int
    verified_at: datetime | None = None

    @classmethod
    def from_domain(cls, value: VerificationSummary) -> "VerificationSummarySchema":
        return cls(**value.__dict__)


class GmailFinalizationInstructionsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apply_label: str = "EmailVault/Vaulted"
    mark_read: bool = False
    archive: bool = False
    enabled: bool = False

    @classmethod
    def from_domain(cls, value: GmailFinalizationInstructions) -> "GmailFinalizationInstructionsSchema":
        return cls(**value.__dict__)


class GmailFinalizationRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    preferences: ArchivePreferencesSchema


class GmailFinalizationRequestResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: ArchiveRecordReferenceSchema
    gmail_finalization: GmailFinalizationInstructionsSchema
    requested_at: datetime

    @classmethod
    def from_domain(cls, value) -> "GmailFinalizationRequestResultSchema":
        return cls(
            record=ArchiveRecordReferenceSchema.from_domain(value.record),
            gmail_finalization=GmailFinalizationInstructionsSchema.from_domain(value.instructions),
            requested_at=value.requested_at,
        )


class GmailFinalizationCallbackRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    succeeded: bool


class ArchiveStateSchema(StrEnum):
    GMAIL_FINALIZATION_PENDING = "GMAIL_FINALIZATION_PENDING"
    GMAIL_FINALIZED = "GMAIL_FINALIZED"
    PRESERVED_GMAIL_FINALIZATION_FAILED = "PRESERVED_GMAIL_FINALIZATION_FAILED"


class GmailFinalizationCallbackResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: ArchiveRecordReferenceSchema
    state: ArchiveStateSchema
    recorded_at: datetime

    @classmethod
    def from_domain(cls, value) -> "GmailFinalizationCallbackResultSchema":
        return cls(
            record=ArchiveRecordReferenceSchema.from_domain(value.record),
            state=ArchiveStateSchema(value.state.value if isinstance(value.state, ArchiveState) else value.state),
            recorded_at=value.recorded_at,
        )


class ArchiveResultSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ArchiveStatusSchema
    record: ArchiveRecordReferenceSchema | None = None
    verification: VerificationSummarySchema | None = None
    gmail_finalization: GmailFinalizationInstructionsSchema = Field(default_factory=GmailFinalizationInstructionsSchema)
    error: ApiErrorSchema | None = None

    @classmethod
    def from_domain(cls, value: ArchiveResult) -> "ArchiveResultSchema":
        return cls(
            status=ArchiveStatusSchema(value.status.value if isinstance(value.status, ArchiveStatus) else value.status),
            record=ArchiveRecordReferenceSchema.from_domain(value.record) if value.record else None,
            verification=VerificationSummarySchema.from_domain(value.verification) if value.verification else None,
            gmail_finalization=GmailFinalizationInstructionsSchema.from_domain(value.gmail_finalization),
            error=ApiErrorSchema(
                category=value.error.category.value,
                message=value.error.message,
                field=value.error.field,
            )
            if value.error
            else None,
        )
