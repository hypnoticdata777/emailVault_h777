from __future__ import annotations

from dataclasses import dataclass

from services.api.app.core.settings import Settings


@dataclass(frozen=True)
class TokenStorageReadiness:
    configured: bool
    missing: tuple[str, ...]
    token_store_path: str
    encryption_key_configured: bool
    stores_plaintext_tokens: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "missing": list(self.missing),
            "token_store_path": self.token_store_path,
            "encryption_key_configured": self.encryption_key_configured,
            "stores_plaintext_tokens": self.stores_plaintext_tokens,
        }


def inspect_token_storage_readiness(settings: Settings) -> TokenStorageReadiness:
    token_store_path = str(settings.token_store_path).strip()
    encryption_key_configured = bool(settings.token_encryption_key.strip())

    missing = []
    if not token_store_path:
        missing.append("EMAIL_VAULT_TOKEN_STORE_PATH")
    if not encryption_key_configured:
        missing.append("EMAIL_VAULT_TOKEN_ENCRYPTION_KEY")

    return TokenStorageReadiness(
        configured=not missing,
        missing=tuple(missing),
        token_store_path=token_store_path,
        encryption_key_configured=encryption_key_configured,
    )
