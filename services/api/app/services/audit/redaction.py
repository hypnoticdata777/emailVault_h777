from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any


SENSITIVE_KEYS = {
    "subject",
    "body",
    "content",
    "email",
    "display_name",
    "original_filename",
    "attachment_name",
    "token",
    "pdf",
}
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: ("[REDACTED]" if key in SENSITIVE_KEYS else redact(inner)) for key, inner in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    return value


def log_safe(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info(message, extra={"email_vault": redact(fields)})

