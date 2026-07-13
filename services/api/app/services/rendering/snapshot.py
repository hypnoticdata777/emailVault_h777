from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.api.app.domain.contracts import Participant, ThreadSnapshot
from services.api.app.services.sanitization.normalize import (
    SanitizedBodyRepresentation,
    SanitizedBodySource,
    normalize_thread_bodies,
)


@dataclass(frozen=True)
class RendererSafeMessageSnapshot:
    message_id: str
    gmail_message_id: str
    sent_at: datetime
    from_participant: Participant
    to: tuple[Participant, ...]
    cc: tuple[Participant, ...]
    bcc: tuple[Participant, ...]
    labels: tuple[str, ...]
    is_read: bool
    safe_html: str | None
    plain_text: str
    blocked_remote_resources: int
    removed_tags: tuple[str, ...]


@dataclass(frozen=True)
class RendererSafeThreadSnapshot:
    thread_id: str
    gmail_thread_id: str
    subject: str
    date_range_start: datetime
    date_range_end: datetime
    messages: tuple[RendererSafeMessageSnapshot, ...]
    blocked_remote_resources: int


def prepare_renderer_safe_thread(thread: ThreadSnapshot) -> RendererSafeThreadSnapshot:
    sanitized_thread = normalize_thread_bodies(thread)
    sanitized_by_message_id = {message.message_id: message for message in sanitized_thread.messages}
    messages = tuple(
        _renderer_message(message, sanitized_by_message_id[message.message_id]) for message in thread.messages
    )
    return RendererSafeThreadSnapshot(
        thread_id=thread.thread_id,
        gmail_thread_id=thread.gmail_thread_id,
        subject=thread.subject,
        date_range_start=thread.date_range_start,
        date_range_end=thread.date_range_end,
        messages=messages,
        blocked_remote_resources=sanitized_thread.blocked_remote_resources,
    )


def _renderer_message(original, sanitized) -> RendererSafeMessageSnapshot:
    return RendererSafeMessageSnapshot(
        message_id=original.message_id,
        gmail_message_id=original.gmail_message_id,
        sent_at=original.sent_at,
        from_participant=original.from_participant,
        to=original.to,
        cc=original.cc,
        bcc=original.bcc,
        labels=original.labels,
        is_read=original.is_read,
        safe_html=_body_content(sanitized.bodies, "text/html", SanitizedBodySource.SANITIZED_HTML),
        plain_text=_required_plain_text(sanitized.bodies),
        blocked_remote_resources=sanitized.blocked_remote_resources,
        removed_tags=sanitized.removed_tags,
    )


def _body_content(
    bodies: tuple[SanitizedBodyRepresentation, ...],
    mime_type: str,
    source: SanitizedBodySource,
) -> str | None:
    for body in bodies:
        if body.mime_type == mime_type and body.source == source:
            return body.content
    return None


def _required_plain_text(bodies: tuple[SanitizedBodyRepresentation, ...]) -> str:
    for body in bodies:
        if body.mime_type == "text/plain":
            return body.content
    raise ValueError("Renderer-safe snapshots require a plain-text body.")

