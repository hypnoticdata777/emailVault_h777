from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from services.api.app.core.settings import Settings


GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class OAuthExchangeError(RuntimeError):
    pass


@dataclass(frozen=True)
class OAuthTokenSet:
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_in: int | None
    scopes: tuple[str, ...]
    id_token: str | None
    received_at: int

    @classmethod
    def from_google_response(
        cls,
        payload: dict[str, Any],
        requested_scopes: tuple[str, ...],
        *,
        now: int | None = None,
    ) -> OAuthTokenSet:
        access_token = str(payload.get("access_token", "")).strip()
        token_type = str(payload.get("token_type", "")).strip()
        if not access_token:
            raise OAuthExchangeError("Google OAuth token response did not include an access token.")
        if not token_type:
            raise OAuthExchangeError("Google OAuth token response did not include a token type.")

        scope_value = str(payload.get("scope", "")).strip()
        scopes = tuple(scope for scope in scope_value.split() if scope) or requested_scopes
        expires_in = payload.get("expires_in")
        return cls(
            access_token=access_token,
            refresh_token=_optional_str(payload.get("refresh_token")),
            token_type=token_type,
            expires_in=int(expires_in) if expires_in is not None else None,
            scopes=scopes,
            id_token=_optional_str(payload.get("id_token")),
            received_at=int(time.time()) if now is None else now,
        )


class GoogleOAuthTokenExchanger:
    def __init__(self, token_endpoint: str = GOOGLE_TOKEN_ENDPOINT, timeout_seconds: int = 10) -> None:
        self.token_endpoint = token_endpoint
        self.timeout_seconds = timeout_seconds

    def exchange_authorization_code(self, code: str, settings: Settings) -> OAuthTokenSet:
        form = parse.urlencode(
            {
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.oauth_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_request = request.Request(
            self.token_endpoint,
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with request.urlopen(token_request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise OAuthExchangeError("Google OAuth token exchange was rejected.") from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OAuthExchangeError("Google OAuth token exchange did not return a usable response.") from exc

        if not isinstance(payload, dict):
            raise OAuthExchangeError("Google OAuth token response was not an object.")
        return OAuthTokenSet.from_google_response(payload, settings.gmail_oauth_scopes)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None
