from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path
from typing import Any

from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import ApiError, ErrorCategory, ThreadSnapshot
from services.api.app.domain.export_package import (
    ExportArtifactKind,
    ExportArtifactPlan,
    ExportPackagePlan,
)
from services.api.app.services.storage.attachments import (
    AttachmentContentProvider,
    NullAttachmentContentProvider,
)
from services.api.app.services.storage.paths import validate_trusted_relative_path


@dataclass(frozen=True)
class WrittenExportArtifact:
    kind: str
    trusted_name: str
    relative_path: str
    content_type: str
    required: bool
    generated: bool
    sha256: str | None
    size_bytes: int | None


@dataclass(frozen=True)
class WrittenExportPackage:
    verified: bool
    package_path: Path
    relative_package_path: str
    artifacts: tuple[WrittenExportArtifact, ...]
    total_bytes: int


def write_export_package(
    export_root: Path,
    package: ExportPackagePlan,
    thread: ThreadSnapshot,
    attachment_content_provider: AttachmentContentProvider | None = None,
) -> WrittenExportPackage:
    """Write a planned local export package and verify generated file checksums."""

    package.validate()
    thread.validate(load_settings())
    provider = attachment_content_provider or NullAttachmentContentProvider()
    record_id = validate_trusted_relative_path(package.record_id)
    relative_package_path = Path(*package.route.relative_parts) / record_id
    relative_package_path_text = "/".join((*package.route.relative_parts, record_id))
    package_path = export_root / relative_package_path

    try:
        package_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Export package path already exists.", "export_package") from exc

    written_by_name: dict[str, WrittenExportArtifact] = {}
    try:
        for artifact in package.artifacts:
            if artifact.kind == ExportArtifactKind.MANIFEST_JSON:
                continue
            content = _artifact_content(artifact, package, thread, provider)
            if content is None:
                continue
            written = _write_and_verify(package_path, relative_package_path, artifact, content)
            written_by_name[artifact.trusted_name] = written

        manifest = _manifest_artifact(package)
        manifest_content = _manifest_content(package, thread, written_by_name)
        written_by_name[manifest.trusted_name] = _write_and_verify(
            package_path,
            relative_package_path,
            manifest,
            manifest_content,
        )
    except Exception:
        shutil.rmtree(package_path, ignore_errors=True)
        raise

    artifacts = tuple(written_by_name[name] for name in sorted(written_by_name))
    return WrittenExportPackage(
        verified=True,
        package_path=package_path,
        relative_package_path=relative_package_path_text,
        artifacts=artifacts,
        total_bytes=sum(artifact.size_bytes or 0 for artifact in artifacts),
    )


def _artifact_content(
    artifact: ExportArtifactPlan,
    package: ExportPackagePlan,
    thread: ThreadSnapshot,
    provider: AttachmentContentProvider,
) -> bytes | None:
    if artifact.kind == ExportArtifactKind.RAW_EML:
        return _raw_eml_content(thread, provider)
    if artifact.kind == ExportArtifactKind.METADATA_JSON:
        return _metadata_content(package, thread)
    if artifact.kind == ExportArtifactKind.NORMALIZED_TEXT:
        return _normalized_text_content(thread)
    if artifact.kind == ExportArtifactKind.ATTACHMENT:
        return _attachment_content(artifact, thread, provider)
    if artifact.required:
        raise ApiError(ErrorCategory.UNEXPECTED_INTERNAL, "Required export artifact writer is missing.", "artifact.kind")
    return None


def _raw_eml_content(thread: ThreadSnapshot, provider: AttachmentContentProvider) -> bytes:
    message = EmailMessage(policy=SMTP)
    message["Subject"] = thread.subject
    message["From"] = thread.messages[0].from_participant.email
    message["To"] = ", ".join(participant.email for participant in thread.messages[0].to)
    message["Date"] = thread.date_range_start.astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")
    message["X-EmailVault-Thread-ID"] = thread.thread_id
    message["X-EmailVault-Gmail-Thread-ID"] = thread.gmail_thread_id
    message.set_content(_normalized_text_content(thread).decode("utf-8"))

    for source in thread.messages:
        for attachment in source.attachments:
            content = provider.fetch_attachment_content(source, attachment)
            if content is None:
                continue
            _verify_attachment_descriptor(attachment, content)
            maintype, _, subtype = attachment.mime_type.partition("/")
            message.add_attachment(
                content,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=attachment.original_filename,
            )

    return message.as_bytes()


def _metadata_content(package: ExportPackagePlan, thread: ThreadSnapshot) -> bytes:
    payload = {
        "schema_version": "email-vault.export-metadata.v1",
        "package": _package_payload(package),
        "thread": {
            "thread_id": thread.thread_id,
            "gmail_thread_id": thread.gmail_thread_id,
            "subject": thread.subject,
            "date_range_start": _iso(thread.date_range_start),
            "date_range_end": _iso(thread.date_range_end),
            "message_count": len(thread.messages),
            "messages": tuple(_message_metadata(message) for message in thread.messages),
        },
    }
    return _json_bytes(payload)


def _normalized_text_content(thread: ThreadSnapshot) -> bytes:
    sections: list[str] = [
        f"Subject: {thread.subject}",
        f"Thread ID: {thread.thread_id}",
        f"Gmail Thread ID: {thread.gmail_thread_id}",
        "",
    ]
    for index, message in enumerate(thread.messages, start=1):
        sections.extend(
            (
                f"Message {index}",
                f"Message ID: {message.message_id}",
                f"Gmail Message ID: {message.gmail_message_id}",
                f"Sent At: {_iso(message.sent_at)}",
                f"From: {message.from_participant.email}",
                f"To: {', '.join(participant.email for participant in message.to)}",
                "",
            )
        )
        for body in message.bodies:
            sections.append(body.content)
            sections.append("")
    return ("\n".join(sections).rstrip() + "\n").encode("utf-8")


def _attachment_content(
    artifact: ExportArtifactPlan,
    thread: ThreadSnapshot,
    provider: AttachmentContentProvider,
) -> bytes:
    for message in thread.messages:
        for attachment in message.attachments:
            if (
                artifact.source_message_id == message.message_id
                and artifact.source_attachment_id == attachment.attachment_id
            ):
                content = provider.fetch_attachment_content(message, attachment)
                if content is None:
                    raise ApiError(ErrorCategory.STORAGE_UNAVAILABLE, "Trusted attachment bytes are required for export.", "attachment")
                _verify_attachment_descriptor(attachment, content)
                return content
    raise ApiError(ErrorCategory.UNEXPECTED_INTERNAL, "Planned attachment artifact has no source descriptor.", "artifact.source_attachment_id")


def _write_and_verify(
    package_path: Path,
    relative_package_path: Path,
    artifact: ExportArtifactPlan,
    content: bytes,
) -> WrittenExportArtifact:
    trusted_name = validate_trusted_relative_path(artifact.trusted_name)
    destination = package_path / trusted_name
    destination.write_bytes(content)
    actual_size = destination.stat().st_size
    actual_hash = _sha256_file(destination)
    expected_hash = hashlib.sha256(content).hexdigest()
    if actual_size != len(content) or actual_hash != expected_hash:
        raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Export artifact verification failed.", "artifact")
    return WrittenExportArtifact(
        kind=artifact.kind.value,
        trusted_name=trusted_name,
        relative_path="/".join((*relative_package_path.parts, trusted_name)),
        content_type=artifact.content_type,
        required=artifact.required,
        generated=True,
        sha256=actual_hash,
        size_bytes=actual_size,
    )


def _manifest_content(
    package: ExportPackagePlan,
    thread: ThreadSnapshot,
    written_by_name: dict[str, WrittenExportArtifact],
) -> bytes:
    payload = {
        "schema_version": "email-vault.export-manifest.v1",
        "package": _package_payload(package),
        "thread": {
            "thread_id": thread.thread_id,
            "gmail_thread_id": thread.gmail_thread_id,
            "message_count": len(thread.messages),
        },
        "artifacts": tuple(_manifest_artifact_payload(artifact, written_by_name) for artifact in package.artifacts),
    }
    return _json_bytes(payload)


def _manifest_artifact(package: ExportPackagePlan) -> ExportArtifactPlan:
    for artifact in package.artifacts:
        if artifact.kind == ExportArtifactKind.MANIFEST_JSON:
            return artifact
    raise ApiError(ErrorCategory.UNEXPECTED_INTERNAL, "Export package is missing a manifest artifact.", "artifacts")


def _manifest_artifact_payload(
    artifact: ExportArtifactPlan,
    written_by_name: dict[str, WrittenExportArtifact],
) -> dict[str, Any]:
    written = written_by_name.get(artifact.trusted_name)
    return {
        "kind": artifact.kind.value,
        "trusted_name": artifact.trusted_name,
        "content_type": artifact.content_type,
        "required": artifact.required,
        "source_message_id": artifact.source_message_id,
        "source_attachment_id": artifact.source_attachment_id,
        "original_filename": artifact.original_filename,
        "generated": written is not None,
        "sha256": written.sha256 if written else None,
        "size_bytes": written.size_bytes if written else None,
    }


def _message_metadata(message) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "gmail_message_id": message.gmail_message_id,
        "sent_at": _iso(message.sent_at),
        "from": asdict(message.from_participant),
        "to": tuple(asdict(participant) for participant in message.to),
        "cc": tuple(asdict(participant) for participant in message.cc),
        "bcc": tuple(asdict(participant) for participant in message.bcc),
        "labels": message.labels,
        "is_read": message.is_read,
        "headers": tuple(asdict(header) for header in message.headers),
        "body_checksums": tuple(
            {
                "mime_type": body.mime_type,
                "sha256": hashlib.sha256(body.content.encode("utf-8")).hexdigest(),
                "size_bytes": len(body.content.encode("utf-8")),
            }
            for body in message.bodies
        ),
        "attachments": tuple(asdict(attachment) for attachment in message.attachments),
    }


def _package_payload(package: ExportPackagePlan) -> dict[str, Any]:
    return {
        "schema_version": package.schema_version,
        "record_id": package.record_id,
        "vault_thread_id": package.vault_thread_id,
        "revision": package.revision,
        "snapshot_sha256": package.snapshot_sha256,
        "gmail_thread_id": package.gmail_thread_id,
        "mode": package.mode.value,
        "route": {
            "layout": package.route.layout.value,
            "category": package.route.category.value,
            "sender_domain": package.route.sender_domain,
            "relative_path": package.route.relative_path,
            "relative_parts": package.route.relative_parts,
        },
    }


def _verify_attachment_descriptor(attachment, content: bytes) -> None:
    if len(content) != attachment.size_bytes:
        raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Attachment size did not match descriptor.", "attachment.size_bytes")
    actual_hash = hashlib.sha256(content).hexdigest()
    if attachment.content_sha256 is not None and actual_hash != attachment.content_sha256:
        raise ApiError(ErrorCategory.STORAGE_VERIFICATION, "Attachment checksum did not match descriptor.", "attachment.content_sha256")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
