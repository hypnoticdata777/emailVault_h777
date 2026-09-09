from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from services.api.app.core.settings import Settings


TOKEN_STORE_VERSION = 1
TOKEN_STORE_KDF_ITERATIONS = 390_000


class TokenStorageError(RuntimeError):
    pass


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


@dataclass(frozen=True)
class StoredOAuthToken:
    provider: str
    owner_id: str
    access_token: str
    refresh_token: str | None
    token_type: str
    scopes: tuple[str, ...]
    expires_at: int | None
    id_token: str | None
    created_at: int
    updated_at: int

    def to_private_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "owner_id": self.owner_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "scopes": list(self.scopes),
            "expires_at": self.expires_at,
            "id_token": self.id_token,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_private_dict(cls, value: dict[str, Any]) -> StoredOAuthToken:
        return cls(
            provider=str(value["provider"]),
            owner_id=str(value["owner_id"]),
            access_token=str(value["access_token"]),
            refresh_token=_optional_str(value.get("refresh_token")),
            token_type=str(value["token_type"]),
            scopes=tuple(str(scope) for scope in value.get("scopes", [])),
            expires_at=_optional_int(value.get("expires_at")),
            id_token=_optional_str(value.get("id_token")),
            created_at=int(value["created_at"]),
            updated_at=int(value["updated_at"]),
        )

    def public_summary(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "owner_id": self.owner_id,
            "token_type": self.token_type,
            "scopes": list(self.scopes),
            "has_refresh_token": bool(self.refresh_token),
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EncryptedLocalTokenStore:
    def __init__(self, path: Path, encryption_key: str) -> None:
        self.path = path
        self.encryption_key = encryption_key

    def save(self, token: StoredOAuthToken) -> None:
        if not self.encryption_key.strip():
            raise TokenStorageError("EMAIL_VAULT_TOKEN_ENCRYPTION_KEY is required.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        salt = os.urandom(16)
        fernet = self._fernet(salt, TOKEN_STORE_KDF_ITERATIONS)
        plaintext = json.dumps(token.to_private_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = {
            "version": TOKEN_STORE_VERSION,
            "cipher": "fernet",
            "kdf": "pbkdf2-sha256",
            "iterations": TOKEN_STORE_KDF_ITERATIONS,
            "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
            "ciphertext": fernet.encrypt(plaintext).decode("ascii"),
        }
        temp_path = self.path.with_name(f"{self.path.name}.tmp")
        temp_path.write_text(json.dumps(envelope, sort_keys=True, indent=2), encoding="utf-8")
        os.replace(temp_path, self.path)

    def load(self) -> StoredOAuthToken:
        if not self.encryption_key.strip():
            raise TokenStorageError("EMAIL_VAULT_TOKEN_ENCRYPTION_KEY is required.")
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
            salt = base64.urlsafe_b64decode(str(envelope["salt"]).encode("ascii"))
            iterations = int(envelope["iterations"])
            ciphertext = str(envelope["ciphertext"]).encode("ascii")
            plaintext = self._fernet(salt, iterations).decrypt(ciphertext)
            return StoredOAuthToken.from_private_dict(json.loads(plaintext.decode("utf-8")))
        except FileNotFoundError as exc:
            raise TokenStorageError("OAuth token store does not exist.") from exc
        except Exception as exc:
            raise TokenStorageError("OAuth token store could not be decrypted.") from exc

    def exists(self) -> bool:
        return self.path.exists()

    def _fernet(self, salt: bytes, iterations: int):
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        except ImportError as exc:
            raise TokenStorageError("Install the api optional dependencies to enable encrypted token storage.") from exc

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode("utf-8")))
        return Fernet(key)


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


def stored_google_oauth_token(
    *,
    owner_id: str,
    access_token: str,
    refresh_token: str | None,
    token_type: str,
    scopes: tuple[str, ...],
    expires_in: int | None,
    id_token: str | None,
    now: int | None = None,
) -> StoredOAuthToken:
    issued_at = int(time.time()) if now is None else now
    expires_at = issued_at + expires_in if expires_in is not None else None
    return StoredOAuthToken(
        provider="google",
        owner_id=owner_id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=token_type,
        scopes=scopes,
        expires_at=expires_at,
        id_token=id_token,
        created_at=issued_at,
        updated_at=issued_at,
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
