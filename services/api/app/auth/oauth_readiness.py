from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from services.api.app.core.settings import PLACEHOLDER_GOOGLE_CLIENT_ID, Settings


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_MUTATION_SCOPES = frozenset(
    {
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.insert",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
    }
)


@dataclass(frozen=True)
class GmailOAuthReadiness:
    configured: bool
    missing: tuple[str, ...]
    client_id_configured: bool
    client_secret_configured: bool
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]
    mutation_scopes_requested: bool
    authorization_endpoint: str = GOOGLE_AUTHORIZATION_ENDPOINT

    def authorization_url(self, state: str = "preview-state") -> str | None:
        if not self.configured:
            return None

        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(self.scopes),
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
                "state": state,
            }
        )
        return f"{self.authorization_endpoint}?{query}"

    def to_dict(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "missing": list(self.missing),
            "client_id_configured": self.client_id_configured,
            "client_secret_configured": self.client_secret_configured,
            "client_id_hint": _client_id_hint(self.client_id),
            "redirect_uri": self.redirect_uri,
            "scopes": list(self.scopes),
            "mutation_scopes_requested": self.mutation_scopes_requested,
            "authorization_endpoint": self.authorization_endpoint,
            "authorization_url_available": self.configured,
        }


def inspect_gmail_oauth_readiness(settings: Settings) -> GmailOAuthReadiness:
    client_id = settings.google_oauth_client_id.strip()
    client_id_configured = bool(client_id) and client_id != PLACEHOLDER_GOOGLE_CLIENT_ID
    client_secret_configured = bool(settings.google_oauth_client_secret.strip())
    redirect_uri = settings.oauth_redirect_uri.strip()
    scopes = tuple(scope.strip() for scope in settings.gmail_oauth_scopes if scope.strip())
    mutation_scopes_requested = any(scope in GMAIL_MUTATION_SCOPES for scope in scopes)

    missing = []
    if not client_id_configured:
        missing.append("GOOGLE_OAUTH_CLIENT_ID")
    if not client_secret_configured:
        missing.append("GOOGLE_OAUTH_CLIENT_SECRET")
    if not redirect_uri:
        missing.append("EMAIL_VAULT_OAUTH_REDIRECT_URI")
    if not scopes:
        missing.append("EMAIL_VAULT_GMAIL_OAUTH_SCOPES")

    return GmailOAuthReadiness(
        configured=not missing,
        missing=tuple(missing),
        client_id_configured=client_id_configured,
        client_secret_configured=client_secret_configured,
        client_id=client_id if client_id_configured else "",
        redirect_uri=redirect_uri,
        scopes=scopes,
        mutation_scopes_requested=mutation_scopes_requested,
    )


def _client_id_hint(client_id: str) -> str:
    if not client_id:
        return ""
    if len(client_id) <= 10:
        return "***"
    return f"{client_id[:6]}...{client_id[-4:]}"
