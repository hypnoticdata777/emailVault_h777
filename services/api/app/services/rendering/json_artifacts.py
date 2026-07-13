from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

from services.api.app.domain.contracts import ArchiveThreadRequest, AttachmentDescriptor, Participant
from services.api.app.services.rendering.manifest import (
    ArtifactManifestPlan,
    PlannedArtifact,
    PlannedArtifactKind,
)
from services.api.app.services.rendering.pdf import RenderedPdfArtifact
from services.api.app.services.rendering.snapshot import RendererSafeMessageSnapshot, RendererSafeThreadSnapshot


@dataclass(frozen=True)
class GeneratedJsonArtifact:
    trusted_name: str
    content_type: str
    content: bytes
    sha256: str
    size_bytes: int


def build_metadata_json_artifact(
    request: ArchiveThreadRequest,
    safe_thread: RendererSafeThreadSnapshot,
    manifest: ArtifactManifestPlan,
) -> GeneratedJsonArtifact:
    """Build the immutable metadata artifact from sanitized archive inputs."""

    planned = _planned_artifact(manifest, PlannedArtifactKind.METADATA_JSON)
    original_messages = {message.message_id: message for message in request.thread.messages}
    payload = {
        "schema_version": "email-vault.metadata.v1",
        "request_id": request.request_id,
        "client_context": {
            "add_on_version": request.client_context.add_on_version,
            "locale": request.client_context.locale,
            "timezone": request.client_context.timezone,
        },
        "preferences": {
            "category": request.preferences.category,
            "mark_read_after_preserve": request.preferences.mark_read_after_preserve,
            "archive_after_preserve": request.preferences.archive_after_preserve,
        },
        "confirmed_at": _iso(request.confirmed_at),
        "record": _record_payload(manifest),
        "thread": {
            "thread_id": safe_thread.thread_id,
            "gmail_thread_id": safe_thread.gmail_thread_id,
            "subject": safe_thread.subject,
            "date_range_start": _iso(safe_thread.date_range_start),
            "date_range_end": _iso(safe_thread.date_range_end),
            "message_count": len(safe_thread.messages),
            "blocked_remote_resources": safe_thread.blocked_remote_resources,
            "messages": tuple(
                _message_payload(message, original_messages[message.message_id].attachments)
                for message in safe_thread.messages
            ),
        },
        "attachment_copy": {
            "status": "descriptor_only",
            "reason": "ArchiveThreadRequest carries attachment descriptors but no attachment bytes yet.",
        },
    }
    return _json_artifact(planned, payload)


def build_manifest_json_artifact(
    manifest: ArtifactManifestPlan,
    generated_artifacts: Iterable[RenderedPdfArtifact | GeneratedJsonArtifact],
) -> GeneratedJsonArtifact:
    """Build the archive manifest after generated artifact bytes exist."""

    planned = _planned_artifact(manifest, PlannedArtifactKind.MANIFEST_JSON)
    generated_by_name = {artifact.trusted_name: artifact for artifact in generated_artifacts}
    payload = {
        "schema_version": "email-vault.manifest.v1",
        "record": _record_payload(manifest),
        "thread": {
            "thread_id": manifest.thread_id,
            "gmail_thread_id": manifest.gmail_thread_id,
            "message_count": manifest.message_count,
            "blocked_remote_resources": manifest.blocked_remote_resources,
        },
        "artifacts": tuple(_manifest_artifact_payload(artifact, generated_by_name) for artifact in manifest.artifacts),
        "attachment_copy": {
            "status": "descriptor_only",
            "reason": "Permitted attachment copy needs attachment bytes or a trusted fetcher in a later phase.",
        },
    }
    return _json_artifact(planned, payload)


def _json_artifact(planned: PlannedArtifact, payload: dict[str, Any]) -> GeneratedJsonArtifact:
    content = (json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return GeneratedJsonArtifact(
        trusted_name=planned.trusted_name,
        content_type=planned.content_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )


def _manifest_artifact_payload(
    planned: PlannedArtifact,
    generated_by_name: dict[str, RenderedPdfArtifact | GeneratedJsonArtifact],
) -> dict[str, Any]:
    generated = generated_by_name.get(planned.trusted_name)
    return {
        "kind": planned.kind.value,
        "trusted_name": planned.trusted_name,
        "content_type": planned.content_type,
        "source_stage": planned.source_stage.value,
        "required": planned.required,
        "generated": generated is not None,
        "sha256": generated.sha256 if generated is not None else None,
        "size_bytes": generated.size_bytes if generated is not None else None,
    }


def _message_payload(
    message: RendererSafeMessageSnapshot,
    attachments: tuple[AttachmentDescriptor, ...],
) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "gmail_message_id": message.gmail_message_id,
        "sent_at": _iso(message.sent_at),
        "from": _participant_payload(message.from_participant),
        "to": tuple(_participant_payload(participant) for participant in message.to),
        "cc": tuple(_participant_payload(participant) for participant in message.cc),
        "bcc": tuple(_participant_payload(participant) for participant in message.bcc),
        "labels": message.labels,
        "is_read": message.is_read,
        "has_safe_html": message.safe_html is not None,
        "safe_html_sha256": _optional_sha256_text(message.safe_html),
        "plain_text_sha256": _sha256_text(message.plain_text),
        "plain_text_size": len(message.plain_text.encode("utf-8")),
        "blocked_remote_resources": message.blocked_remote_resources,
        "removed_tags": message.removed_tags,
        "attachments": tuple(_attachment_payload(attachment) for attachment in attachments),
    }


def _attachment_payload(attachment: AttachmentDescriptor) -> dict[str, Any]:
    return {
        "attachment_id": attachment.attachment_id,
        "original_filename": attachment.original_filename,
        "mime_type": attachment.mime_type,
        "size_bytes": attachment.size_bytes,
        "content_sha256": attachment.content_sha256,
        "copy_status": "descriptor_only",
    }


def _participant_payload(participant: Participant) -> dict[str, Any]:
    return {"email": participant.email, "display_name": participant.display_name}


def _record_payload(manifest: ArtifactManifestPlan) -> dict[str, Any]:
    return {
        "record_id": manifest.record_id,
        "vault_thread_id": manifest.vault_thread_id,
        "revision": manifest.revision,
        "snapshot_sha256": manifest.snapshot_sha256,
    }


def _planned_artifact(manifest: ArtifactManifestPlan, kind: PlannedArtifactKind) -> PlannedArtifact:
    for artifact in manifest.artifacts:
        if artifact.kind == kind:
            return artifact
    raise ValueError(f"Artifact manifest is missing {kind.value}.")


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    return value


def _iso(value: datetime) -> str:
    normalized = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return normalized.isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_sha256_text(value: str | None) -> str | None:
    return _sha256_text(value) if value is not None else None
