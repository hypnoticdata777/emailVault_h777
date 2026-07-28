from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


PLACEHOLDER_GOOGLE_CLIENT_ID = "replace-with-google-oauth-client-id"
DEFAULT_ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "text/csv",
        "image/jpeg",
        "image/png",
    }
)
DEFAULT_ALLOWED_EXTENSIONS = frozenset({".pdf", ".txt", ".csv", ".jpg", ".jpeg", ".png"})


@dataclass(frozen=True)
class Settings:
    environment: str = "local"
    storage_root: Path = Path(".local/email-vault-storage")
    max_attachments: int = 10
    max_attachment_bytes: int = 10 * 1024 * 1024
    max_total_payload_bytes: int = 25 * 1024 * 1024
    allowed_mime_types: frozenset[str] = field(default_factory=lambda: DEFAULT_ALLOWED_MIME_TYPES)
    allowed_extensions: frozenset[str] = field(default_factory=lambda: DEFAULT_ALLOWED_EXTENSIONS)
    identity_verifier: str = "synthetic"
    google_oauth_client_id: str = PLACEHOLDER_GOOGLE_CLIENT_ID
    addon_signing_secret: str = ""
    addon_signature_max_age_seconds: int = 300
    database_url: str = "sqlite:///./email_vault.db"
    web_session_secret: str = ""
    admin_password: str = ""


def _split_csv(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def load_settings() -> Settings:
    return Settings(
        environment=os.getenv("EMAIL_VAULT_ENV", "local"),
        storage_root=Path(os.getenv("EMAIL_VAULT_STORAGE_ROOT", ".local/email-vault-storage")),
        max_attachments=int(os.getenv("EMAIL_VAULT_MAX_ATTACHMENTS", "10")),
        max_attachment_bytes=int(os.getenv("EMAIL_VAULT_MAX_ATTACHMENT_BYTES", str(10 * 1024 * 1024))),
        max_total_payload_bytes=int(os.getenv("EMAIL_VAULT_MAX_TOTAL_PAYLOAD_BYTES", str(25 * 1024 * 1024))),
        allowed_mime_types=_split_csv(
            os.getenv("EMAIL_VAULT_ALLOWED_ATTACHMENT_TYPES", ",".join(sorted(DEFAULT_ALLOWED_MIME_TYPES)))
        ),
        allowed_extensions=_split_csv(
            os.getenv("EMAIL_VAULT_ALLOWED_ATTACHMENT_EXTENSIONS", ",".join(sorted(DEFAULT_ALLOWED_EXTENSIONS)))
        ),
        identity_verifier=os.getenv("EMAIL_VAULT_IDENTITY_VERIFIER", "synthetic").strip().lower(),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID", PLACEHOLDER_GOOGLE_CLIENT_ID),
        addon_signing_secret=os.getenv("EMAIL_VAULT_ADDON_SIGNING_SECRET", ""),
        addon_signature_max_age_seconds=int(os.getenv("EMAIL_VAULT_ADDON_SIGNATURE_MAX_AGE_SECONDS", "300")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./email_vault.db"),
        web_session_secret=os.getenv("EMAIL_VAULT_WEB_SESSION_SECRET", ""),
        admin_password=os.getenv("EMAIL_VAULT_ADMIN_PASSWORD", ""),
    )
