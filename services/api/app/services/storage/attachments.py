from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from services.api.app.domain.contracts import (
    ApiError,
    AttachmentDescriptor,
    ErrorCategory,
    MessageSnapshot,
    ThreadSnapshot,
)
from services.api.app.services.rendering.manifest import (
    ArtifactManifestPlan,
    PlannedArtifact,
    PlannedArtifactKind,
)


@dataclass(frozen=True)
class GeneratedAttachmentArtifact:
    trusted_name: str
    content_type: str
    content: bytes
    sha256: str
    size_bytes: int
    source_message_id: str
    source_attachment_id: str
    original_filename: str


@dataclass(frozen=True)
class AttachmentCopyStatus:
    source_message_id: str
    source_attachment_id: str
    original_filename: str
    mime_type: str
    expected_size_bytes: int
    expected_sha256: str | None
    copy_status: str
    trusted_name: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class AttachmentCopyResult:
    artifacts: tuple[GeneratedAttachmentArtifact, ...]
    statuses: tuple[AttachmentCopyStatus, ...]


class AttachmentContentProvider(Protocol):
    def fetch_attachment_content(self, message: MessageSnapshot, attachment: AttachmentDescriptor) -> bytes | None:
        raise NotImplementedError


class NullAttachmentContentProvider:
    def fetch_attachment_content(self, message: MessageSnapshot, attachment: AttachmentDescriptor) -> bytes | None:
        del message, attachment
        return None


def build_attachment_copy_artifacts(
    thread: ThreadSnapshot,
    manifest: ArtifactManifestPlan,
    content_provider: AttachmentContentProvider,
) -> AttachmentCopyResult:
    """Copy permitted attachment bytes only when a trusted provider supplies them."""

    planned_by_source = {
        (artifact.source_message_id, artifact.source_attachment_id): artifact
        for artifact in manifest.artifacts
        if artifact.kind == PlannedArtifactKind.ATTACHMENT_COPY
    }
    artifacts: list[GeneratedAttachmentArtifact] = []
    statuses: list[AttachmentCopyStatus] = []

    for message in thread.messages:
        for attachment in message.attachments:
            planned = planned_by_source.get((message.message_id, attachment.attachment_id))
            if planned is None:
                raise ApiError(ErrorCategory.UNEXPECTED_INTERNAL, "Attachment copy plan is missing.", "attachments")

            content = content_provider.fetch_attachment_content(message, attachment)
            if content is None:
                statuses.append(_status(attachment, message.message_id, "descriptor_only", reason="trusted bytes unavailable"))
                continue

            generated = _generated_attachment_artifact(message.message_id, attachment, planned, content)
            artifacts.append(generated)
            statuses.append(
                _status(
                    attachment,
                    message.message_id,
                    "copied",
                    trusted_name=generated.trusted_name,
                    sha256=generated.sha256,
                    size_bytes=generated.size_bytes,
                )
            )

    return AttachmentCopyResult(artifacts=tuple(artifacts), statuses=tuple(statuses))


def _generated_attachment_artifact(
    message_id: str,
    attachment: AttachmentDescriptor,
    planned: PlannedArtifact,
    content: bytes,
) -> GeneratedAttachmentArtifact:
    actual_size = len(content)
    if actual_size != attachment.size_bytes:
        raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Attachment size did not match descriptor.", "attachment.size_bytes")

    actual_sha256 = hashlib.sha256(content).hexdigest()
    if attachment.content_sha256 is not None:
        if len(attachment.content_sha256) != 64:
            raise ApiError(ErrorCategory.INVALID_SCHEMA, "Attachment SHA-256 must be 64 hex characters.", "attachment.content_sha256")
        if actual_sha256 != attachment.content_sha256:
            raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Attachment checksum did not match descriptor.", "attachment.content_sha256")

    return GeneratedAttachmentArtifact(
        trusted_name=planned.trusted_name,
        content_type=planned.content_type,
        content=content,
        sha256=actual_sha256,
        size_bytes=actual_size,
        source_message_id=message_id,
        source_attachment_id=attachment.attachment_id,
        original_filename=attachment.original_filename,
    )


def _status(
    attachment: AttachmentDescriptor,
    message_id: str,
    copy_status: str,
    trusted_name: str | None = None,
    sha256: str | None = None,
    size_bytes: int | None = None,
    reason: str | None = None,
) -> AttachmentCopyStatus:
    return AttachmentCopyStatus(
        source_message_id=message_id,
        source_attachment_id=attachment.attachment_id,
        original_filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        expected_size_bytes=attachment.size_bytes,
        expected_sha256=attachment.content_sha256,
        copy_status=copy_status,
        trusted_name=trusted_name,
        sha256=sha256,
        size_bytes=size_bytes,
        reason=reason,
    )
