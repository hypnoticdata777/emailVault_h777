from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from services.api.app.domain.contracts import (
    ArchivePreferences,
    ArchiveThreadRequest,
    AttachmentDescriptor,
    BodyRepresentation,
    ClientContext,
    MessageHeader,
    MessageSnapshot,
    Participant,
    ThreadSnapshot,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "emails"


def _participant(raw: dict) -> Participant:
    return Participant(email=raw["email"], display_name=raw.get("display_name"))


def _attachment(raw: dict) -> AttachmentDescriptor:
    return AttachmentDescriptor(
        attachment_id=raw["attachment_id"],
        original_filename=raw["original_filename"],
        mime_type=raw["mime_type"],
        size_bytes=raw["size_bytes"],
        content_sha256=raw.get("content_sha256"),
    )


def _header(raw: dict) -> MessageHeader:
    return MessageHeader(name=raw["name"], value=raw.get("value", ""))


def _message(raw: dict) -> MessageSnapshot:
    return MessageSnapshot(
        message_id=raw["message_id"],
        gmail_message_id=raw["gmail_message_id"],
        sent_at=datetime.fromisoformat(raw["sent_at"]),
        from_participant=_participant(raw["from"]),
        to=tuple(_participant(item) for item in raw.get("to", [])),
        cc=tuple(_participant(item) for item in raw.get("cc", [])),
        bcc=tuple(_participant(item) for item in raw.get("bcc", [])),
        labels=tuple(raw.get("labels", [])),
        is_read=raw.get("is_read", False),
        headers=tuple(_header(item) for item in raw.get("headers", [])),
        bodies=tuple(BodyRepresentation(**item) for item in raw.get("bodies", [])),
        attachments=tuple(_attachment(item) for item in raw.get("attachments", [])),
    )


def load_fixture(name: str) -> ArchiveThreadRequest:
    raw = json.loads((FIXTURE_ROOT / f"{name}.json").read_text(encoding="utf-8"))
    thread = raw["thread"]
    return ArchiveThreadRequest(
        request_id=raw["request_id"],
        client_context=ClientContext(**raw["client_context"]),
        preferences=ArchivePreferences(**raw["preferences"]),
        confirmed_at=datetime.fromisoformat(raw["confirmed_at"]),
        thread=ThreadSnapshot(
            thread_id=thread["thread_id"],
            gmail_thread_id=thread["gmail_thread_id"],
            subject=thread["subject"],
            date_range_start=datetime.fromisoformat(thread["date_range_start"]),
            date_range_end=datetime.fromisoformat(thread["date_range_end"]),
            messages=tuple(_message(item) for item in thread["messages"]),
        ),
    )
