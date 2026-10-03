from __future__ import annotations

import hashlib
import html
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from services.api.app.domain.contracts import ApiError, ErrorCategory
from services.api.app.services.rendering.manifest import (
    ArtifactManifestPlan,
    PlannedArtifact,
    PlannedArtifactKind,
)
from services.api.app.services.rendering.snapshot import RendererSafeMessageSnapshot, RendererSafeThreadSnapshot


BLOCKED_NETWORK_RESOURCE_TYPES: tuple[str, ...] = (
    "document",
    "stylesheet",
    "image",
    "media",
    "font",
    "script",
    "texttrack",
    "xhr",
    "fetch",
    "eventsource",
    "websocket",
    "manifest",
    "other",
)


@dataclass(frozen=True)
class PdfRenderPolicy:
    javascript_enabled: bool = False
    block_network: bool = True
    blocked_resource_types: tuple[str, ...] = BLOCKED_NETWORK_RESOURCE_TYPES


@dataclass(frozen=True)
class RenderedPdfArtifact:
    trusted_name: str
    content_type: str
    content: bytes
    sha256: str
    size_bytes: int


class PdfRendererAdapter(Protocol):
    def render_pdf(self, html_content: str, output_path: Path, policy: PdfRenderPolicy) -> None:
        raise NotImplementedError


def render_pdf_from_safe_thread(
    safe_thread: RendererSafeThreadSnapshot,
    manifest: ArtifactManifestPlan,
    adapter: PdfRendererAdapter,
    temp_root: Path | None = None,
) -> RenderedPdfArtifact:
    pdf_artifact = _planned_pdf_artifact(manifest)
    html_content = build_renderer_html(safe_thread)
    policy = PdfRenderPolicy()

    try:
        with tempfile.TemporaryDirectory(prefix="email-vault-render-", dir=temp_root) as workspace:
            output_path = Path(workspace) / pdf_artifact.trusted_name
            adapter.render_pdf(html_content, output_path, policy)
            if not output_path.is_file():
                raise ApiError(ErrorCategory.SANITIZATION_RENDERING, "PDF renderer did not produce an output file.", "pdf")
            content = output_path.read_bytes()
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(ErrorCategory.SANITIZATION_RENDERING, "PDF rendering failed.", "pdf") from exc

    return RenderedPdfArtifact(
        trusted_name=pdf_artifact.trusted_name,
        content_type=pdf_artifact.content_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )


def build_renderer_html(safe_thread: RendererSafeThreadSnapshot) -> str:
    message_html = "\n".join(_message_html(message) for message in safe_thread.messages)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(safe_thread.subject)}</title>\n"
        "<style>\n"
        "body{font-family:Arial,sans-serif;color:#111;line-height:1.45;margin:32px;}\n"
        "article{border-top:1px solid #ccc;padding:16px 0;}\n"
        ".meta{color:#555;font-size:12px;margin-bottom:10px;}\n"
        "pre{white-space:pre-wrap;font-family:inherit;}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>{html.escape(safe_thread.subject)}</h1>\n"
        f'<p class="meta">Messages: {len(safe_thread.messages)} | '
        f"Blocked remote resources: {safe_thread.blocked_remote_resources}</p>\n"
        f"{message_html}\n"
        "</body>\n"
        "</html>\n"
    )


def _planned_pdf_artifact(manifest: ArtifactManifestPlan) -> PlannedArtifact:
    for artifact in manifest.artifacts:
        if artifact.kind == PlannedArtifactKind.PDF:
            return artifact
    raise ApiError(ErrorCategory.SANITIZATION_RENDERING, "Artifact manifest is missing a PDF output.", "artifacts")


def _message_html(message: RendererSafeMessageSnapshot) -> str:
    body = message.safe_html if message.safe_html is not None else f"<pre>{html.escape(message.plain_text)}</pre>"
    return (
        "<article>\n"
        f"<h2>{html.escape(message.from_participant.display_name or message.from_participant.email)}</h2>\n"
        f'<p class="meta">Sent: {html.escape(message.sent_at.isoformat())} | '
        f"Labels: {html.escape(', '.join(message.labels))}</p>\n"
        f"{body}\n"
        "</article>"
    )
