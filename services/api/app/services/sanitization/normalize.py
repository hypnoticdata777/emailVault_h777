from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from services.api.app.domain.contracts import MessageSnapshot, ThreadSnapshot
from services.api.app.services.sanitization.html import SanitizedHtml, sanitize_email_html


class SanitizedBodySource(StrEnum):
    ORIGINAL_TEXT = "ORIGINAL_TEXT"
    SANITIZED_HTML = "SANITIZED_HTML"
    PLAIN_TEXT_FALLBACK = "PLAIN_TEXT_FALLBACK"


@dataclass(frozen=True)
class SanitizedBodyRepresentation:
    mime_type: str
    content: str
    source: SanitizedBodySource


@dataclass(frozen=True)
class SanitizedMessageSnapshot:
    message_id: str
    gmail_message_id: str
    bodies: tuple[SanitizedBodyRepresentation, ...]
    blocked_remote_resources: int
    removed_tags: tuple[str, ...]


@dataclass(frozen=True)
class SanitizedThreadSnapshot:
    thread_id: str
    gmail_thread_id: str
    messages: tuple[SanitizedMessageSnapshot, ...]
    blocked_remote_resources: int


def normalize_message_bodies(message: MessageSnapshot) -> SanitizedMessageSnapshot:
    bodies: list[SanitizedBodyRepresentation] = []
    blocked_remote_resources = 0
    removed_tags: list[str] = []
    fallback_texts: list[str] = []

    for body in message.bodies:
        if body.mime_type == "text/plain":
            bodies.append(
                SanitizedBodyRepresentation(
                    mime_type="text/plain",
                    content=body.content,
                    source=SanitizedBodySource.ORIGINAL_TEXT,
                )
            )
            fallback_texts.append(body.content)
            continue

        if body.mime_type == "text/html":
            sanitized = sanitize_email_html(body.content)
            bodies.append(_html_body(sanitized))
            fallback_texts.append(sanitized.plain_text)
            blocked_remote_resources += sanitized.blocked_remote_resources
            removed_tags.extend(sanitized.removed_tags)

    if not any(body.mime_type == "text/plain" for body in bodies):
        bodies.append(
            SanitizedBodyRepresentation(
                mime_type="text/plain",
                content=_fallback_text(fallback_texts),
                source=SanitizedBodySource.PLAIN_TEXT_FALLBACK,
            )
        )

    return SanitizedMessageSnapshot(
        message_id=message.message_id,
        gmail_message_id=message.gmail_message_id,
        bodies=tuple(bodies),
        blocked_remote_resources=blocked_remote_resources,
        removed_tags=tuple(removed_tags),
    )


def normalize_thread_bodies(thread: ThreadSnapshot) -> SanitizedThreadSnapshot:
    messages = tuple(normalize_message_bodies(message) for message in thread.messages)
    return SanitizedThreadSnapshot(
        thread_id=thread.thread_id,
        gmail_thread_id=thread.gmail_thread_id,
        messages=messages,
        blocked_remote_resources=sum(message.blocked_remote_resources for message in messages),
    )


def _html_body(sanitized: SanitizedHtml) -> SanitizedBodyRepresentation:
    return SanitizedBodyRepresentation(
        mime_type="text/html",
        content=sanitized.html,
        source=SanitizedBodySource.SANITIZED_HTML,
    )


def _fallback_text(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())
