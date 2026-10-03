from __future__ import annotations

import hashlib
import hmac
import html
import time
from dataclasses import dataclass
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from services.api.app.auth.oauth_exchange import GoogleOAuthTokenExchanger, OAuthExchangeError
from services.api.app.auth.oauth_readiness import GmailOAuthReadiness, inspect_gmail_oauth_readiness
from services.api.app.auth.token_storage import (
    EncryptedLocalTokenStore,
    TokenStorageError,
    TokenStorageReadiness,
    inspect_token_storage_readiness,
    stored_google_oauth_token,
)
from services.api.app.core.settings import Settings, load_settings


router = APIRouter()

SESSION_COOKIE = "email_vault_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60
OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60


@router.get("/login", response_class=HTMLResponse)
async def login_page() -> HTMLResponse:
    return HTMLResponse(_render_login_html())


@router.post("/login/demo")
async def demo_login() -> RedirectResponse:
    response = RedirectResponse("/demo", status_code=303)
    _set_session_cookie(response, "demo")
    return response


@router.post("/login/admin", response_class=HTMLResponse)
async def admin_login(request: Request) -> Response:
    settings = load_settings()
    if not _admin_login_configured(settings.admin_password, settings.web_session_secret):
        return HTMLResponse(
            _render_login_html(
                "Admin login is disabled until EMAIL_VAULT_ADMIN_PASSWORD and "
                "EMAIL_VAULT_WEB_SESSION_SECRET are configured locally."
            ),
            status_code=503,
        )

    form = parse_qs((await request.body()).decode("utf-8"))
    submitted_password = form.get("password", [""])[0]
    if not hmac.compare_digest(submitted_password, settings.admin_password):
        return HTMLResponse(_render_login_html("Admin password did not match."), status_code=401)

    response = RedirectResponse("/admin", status_code=303)
    _set_session_cookie(response, "admin")
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")
    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_console(request: Request) -> Response:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    settings = load_settings()
    oauth_readiness = inspect_gmail_oauth_readiness(settings)
    token_storage_readiness = inspect_token_storage_readiness(settings)
    return HTMLResponse(
        _render_admin_html(
            oauth_readiness,
            token_storage_readiness,
            _admin_authorization_url(settings, oauth_readiness, token_storage_readiness),
        )
    )


@router.get("/admin/gmail/oauth/readiness", response_model=None)
async def gmail_oauth_readiness(request: Request) -> Response | dict[str, object]:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    return inspect_gmail_oauth_readiness(load_settings()).to_dict()


@router.get("/admin/gmail/token-storage/readiness", response_model=None)
async def gmail_token_storage_readiness(request: Request) -> Response | dict[str, object]:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    return inspect_token_storage_readiness(load_settings()).to_dict()


@router.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(request: Request) -> Response:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    settings = load_settings()
    error = request.query_params.get("error", "")
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    oauth_readiness = inspect_gmail_oauth_readiness(settings)
    token_storage_readiness = inspect_token_storage_readiness(settings)
    exchange_result = _handle_google_oauth_callback(
        settings=settings,
        error=error,
        code=code,
        state=state,
        oauth_readiness=oauth_readiness,
        token_storage_readiness=token_storage_readiness,
    )
    return HTMLResponse(
        _render_oauth_callback_html(
            exchange_result=exchange_result,
            code_present=bool(code),
            state_present=bool(state),
            oauth_readiness=oauth_readiness,
            token_storage_readiness=token_storage_readiness,
        )
    )


@dataclass(frozen=True)
class OAuthCallbackExchangeResult:
    status: str
    title: str
    detail: str
    token_summary: dict[str, object] | None = None


def _admin_login_configured(admin_password: str, web_session_secret: str) -> bool:
    return bool(admin_password.strip()) and bool(web_session_secret.strip())


def _set_session_cookie(response: Response, role: str) -> None:
    settings = load_settings()
    secret = settings.web_session_secret.strip()
    if not secret:
        return

    issued_at = str(int(time.time()))
    payload = f"{role}:{issued_at}"
    signature = _sign_payload(payload, secret)
    response.set_cookie(
        SESSION_COOKIE,
        f"{payload}:{signature}",
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )


def _session_role(request: Request) -> str | None:
    settings = load_settings()
    secret = settings.web_session_secret.strip()
    if not secret:
        return None

    raw_cookie = request.cookies.get(SESSION_COOKIE, "")
    try:
        role, issued_at, signature = raw_cookie.split(":", 2)
        issued_timestamp = int(issued_at)
    except ValueError:
        return None

    if role not in {"admin", "demo"}:
        return None
    if int(time.time()) - issued_timestamp > SESSION_MAX_AGE_SECONDS:
        return None

    expected_signature = _sign_payload(f"{role}:{issued_at}", secret)
    if not hmac.compare_digest(signature, expected_signature):
        return None
    return role


def _sign_payload(payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _admin_authorization_url(
    settings: Settings,
    readiness: GmailOAuthReadiness,
    token_storage: TokenStorageReadiness,
) -> str | None:
    if not readiness.configured or not token_storage.configured:
        return None
    return readiness.authorization_url(_build_oauth_state(settings))


def _build_oauth_state(settings: Settings) -> str:
    issued_at = str(int(time.time()))
    payload = f"gmail-oauth:{issued_at}"
    signature = _sign_payload(payload, settings.web_session_secret)
    return f"{payload}:{signature}"


def _oauth_state_valid(state: str, settings: Settings) -> bool:
    secret = settings.web_session_secret.strip()
    if not state or not secret:
        return False
    try:
        purpose, issued_at, signature = state.split(":", 2)
        issued_timestamp = int(issued_at)
    except ValueError:
        return False
    if purpose != "gmail-oauth":
        return False
    if int(time.time()) - issued_timestamp > OAUTH_STATE_MAX_AGE_SECONDS:
        return False
    expected_signature = _sign_payload(f"{purpose}:{issued_at}", secret)
    return hmac.compare_digest(signature, expected_signature)


def _handle_google_oauth_callback(
    *,
    settings: Settings,
    error: str,
    code: str,
    state: str,
    oauth_readiness: GmailOAuthReadiness,
    token_storage_readiness: TokenStorageReadiness,
) -> OAuthCallbackExchangeResult:
    if error:
        return OAuthCallbackExchangeResult(
            status="error",
            title="OAuth Callback Error",
            detail=f"Google returned an OAuth error: {error}.",
        )
    if not code:
        return OAuthCallbackExchangeResult(
            status="ready",
            title="OAuth Callback Ready",
            detail="Callback route is reachable. No authorization code was supplied.",
        )
    if not oauth_readiness.configured or not token_storage_readiness.configured:
        return OAuthCallbackExchangeResult(
            status="blocked",
            title="OAuth Callback Blocked",
            detail="Authorization code was received, but token exchange is blocked until OAuth and token-storage config are complete.",
        )
    if not _oauth_state_valid(state, settings):
        return OAuthCallbackExchangeResult(
            status="blocked",
            title="OAuth State Rejected",
            detail="Authorization code was received, but the OAuth state parameter did not match this admin session.",
        )

    try:
        token_summary = _exchange_and_store_google_tokens(settings, code)
    except (OAuthExchangeError, TokenStorageError) as exc:
        return OAuthCallbackExchangeResult(
            status="error",
            title="OAuth Token Exchange Failed",
            detail=str(exc),
        )
    return OAuthCallbackExchangeResult(
        status="stored",
        title="Gmail Token Stored",
        detail="Authorization code was exchanged and encrypted token storage was updated locally.",
        token_summary=token_summary,
    )


def _exchange_and_store_google_tokens(settings: Settings, code: str) -> dict[str, object]:
    token_set = GoogleOAuthTokenExchanger().exchange_authorization_code(code, settings)
    stored_token = stored_google_oauth_token(
        owner_id="local-admin",
        access_token=token_set.access_token,
        refresh_token=token_set.refresh_token,
        token_type=token_set.token_type,
        scopes=token_set.scopes,
        expires_in=token_set.expires_in,
        id_token=token_set.id_token,
        now=token_set.received_at,
    )
    EncryptedLocalTokenStore(settings.token_store_path, settings.token_encryption_key).save(stored_token)
    return stored_token.public_summary()


def _render_login_html(message: str = "") -> str:
    safe_message = html.escape(message)
    message_html = f'<p class="notice">{safe_message}</p>' if safe_message else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Email Vault Access</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #16201d;
      --muted: #64706c;
      --line: #d8dfdc;
      --paper: #ffffff;
      --page: #edf2ef;
      --accent: #256f5b;
      --accent-2: #365f91;
      --danger: #b6472f;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--page);
      color: var(--ink);
    }}
    main {{
      width: min(980px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 36px 0;
    }}
    header {{
      display: grid;
      gap: 8px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0;
      font-size: 30px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 17px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }}
    .notice {{
      margin-top: 14px;
      padding: 10px 12px;
      border: 1px solid #e8c5b8;
      border-radius: 8px;
      color: #80341d;
      background: #fff3ee;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 20px;
      align-items: stretch;
    }}
    section {{
      display: grid;
      gap: 16px;
      align-content: start;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-height: 248px;
    }}
    label {{
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    input {{
      width: 100%;
      height: 42px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }}
    button, a.button {{
      display: inline-flex;
      justify-content: center;
      align-items: center;
      min-height: 42px;
      padding: 9px 14px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
    }}
    button.secondary {{
      background: var(--accent-2);
    }}
    .status {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 18px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 7px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--paper);
      font-size: 13px;
      color: var(--ink);
      white-space: nowrap;
    }}
    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
    }}
    .dot.warn {{ background: var(--danger); }}
    @media (max-width: 720px) {{
      .grid {{ grid-template-columns: 1fr; }}
      main {{ width: min(100% - 24px, 980px); padding-top: 24px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Email Vault Access</h1>
      <p>Use the synthetic demo for portfolio review, or enter the private admin console when local credentials are configured.</p>
      {message_html}
    </header>
    <div class="status">
      <span class="pill"><span class="dot"></span> Demo uses synthetic data</span>
      <span class="pill"><span class="dot warn"></span> Gmail live access is not connected here</span>
    </div>
    <div class="grid">
      <section>
        <div>
          <h2>Demo Access</h2>
          <p>Preview the read-only review queue without Gmail credentials, file writes, or mailbox changes.</p>
        </div>
        <form method="post" action="/login/demo">
          <button type="submit">Open Demo</button>
        </form>
      </section>
      <section>
        <div>
          <h2>Admin Access</h2>
          <p>Private local control area for the owner. This is where live Gmail controls can be added after OAuth and token storage are ready.</p>
        </div>
        <form method="post" action="/login/admin">
          <div>
            <label for="password">Admin Password</label>
            <input id="password" name="password" type="password" autocomplete="current-password">
          </div>
          <button class="secondary" type="submit">Enter Admin</button>
        </form>
      </section>
    </div>
  </main>
</body>
</html>"""


def _render_admin_html(
    readiness: GmailOAuthReadiness,
    token_storage: TokenStorageReadiness,
    authorization_url: str | None,
) -> str:
    category_flow = _admin_category_flow()
    oauth_status = "Ready" if readiness.configured else "Needs config"
    missing_items = "".join(f"<li>{html.escape(item)}</li>" for item in readiness.missing)
    missing_html = f"<ul>{missing_items}</ul>" if missing_items else "<p>Read-only Gmail OAuth config is present.</p>"
    scope_items = "".join(f"<li>{html.escape(scope)}</li>" for scope in readiness.scopes)
    scope_html = f"<ul>{scope_items}</ul>" if scope_items else "<p>No Gmail scopes are configured.</p>"
    mutation_copy = (
        "Mutation-capable scopes are present. Review before live use."
        if readiness.mutation_scopes_requested
        else "Read-only import scope only. Cleanup/mutation scopes are not requested."
    )
    readiness_json_link = "/admin/gmail/oauth/readiness"
    token_status = "Ready" if token_storage.configured else "Needs config"
    token_missing_items = "".join(f"<li>{html.escape(item)}</li>" for item in token_storage.missing)
    token_missing_html = (
        f"<ul>{token_missing_items}</ul>"
        if token_missing_items
        else "<p>Token storage config is present. Token exchange can run from the signed OAuth callback.</p>"
    )
    token_readiness_json_link = "/admin/gmail/token-storage/readiness"
    connect_html = (
        f'<a class="button" href="{html.escape(authorization_url, quote=True)}">Connect Read-Only Gmail</a>'
        if authorization_url
        else "<p>Connect is hidden until OAuth and token-storage config are both ready.</p>"
    )
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Email Vault Admin</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #16201d;
      --muted: #64706c;
      --line: #d8dfdc;
      --paper: #ffffff;
      --page: #edf2ef;
      --accent: #256f5b;
      --accent-2: #365f91;
      --danger: #b6472f;
      --gold: #c08a2d;
      --blue-soft: #eaf1fb;
      --green-soft: #e8f5ef;
      --gold-soft: #fff6e5;
      --rose-soft: #fff0ec;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--page);
      color: var(--ink);
    }
    main {
      width: min(1100px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 36px;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }
    .hero-band {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 20px;
      align-items: center;
      margin-top: 18px;
      padding: 18px;
      border: 1px solid #cbd7d2;
      border-radius: 8px;
      background: linear-gradient(135deg, #ffffff 0%, #e8f5ef 46%, #eaf1fb 100%);
    }
    .tabbar {
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.88);
      backdrop-filter: blur(10px);
    }
    .tabbar a {
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 7px 10px;
      border-radius: 8px;
      color: var(--ink);
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
    }
    .tabbar a:first-child {
      background: #17201b;
      color: #ffffff;
    }
    .brand-line {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }
    .brand-mark {
      display: inline-grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 8px;
      background: #17201b;
      color: #ffffff;
      font-size: 22px;
      font-weight: 800;
    }
    .hero-band strong {
      display: block;
      font-size: 16px;
      line-height: 1.25;
    }
    .hero-band p {
      max-width: 720px;
    }
    .hero-stat {
      display: grid;
      gap: 4px;
      min-width: 172px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255,255,255,.72);
    }
    .hero-stat span {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .hero-stat strong {
      font-size: 24px;
    }
    h1 {
      margin: 0;
      font-size: 30px;
      line-height: 1.15;
      letter-spacing: 0;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 18px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    p {
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    form { margin: 0; }
    button, a.button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      padding: 8px 12px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      text-decoration: none;
      cursor: pointer;
      white-space: nowrap;
    }
    .button.secondary, button.secondary { background: var(--accent-2); }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
      gap: 16px;
      margin-top: 18px;
      align-items: start;
    }
    section, .metric {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    section {
      min-width: 0;
      padding: 18px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }
    .metric {
      min-width: 0;
      min-height: 92px;
      padding: 14px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .metric strong {
      display: block;
      margin-top: 9px;
      font-size: 22px;
      line-height: 1.15;
    }
    .mode-grid, .pipeline {
      display: grid;
      gap: 10px;
    }
    .mode-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .mode-card {
      min-width: 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--green-soft);
    }
    .mode-card.clean { background: var(--blue-soft); }
    .mode-card.free { background: var(--gold-soft); }
    .mode-card span, .step span {
      display: block;
      margin-top: 5px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .pipeline {
      grid-template-columns: repeat(4, minmax(0, 1fr));
      counter-reset: pipeline;
    }
    .step {
      position: relative;
      min-width: 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--paper);
    }
    .step::before {
      counter-increment: pipeline;
      content: counter(pipeline);
      display: inline-grid;
      place-items: center;
      width: 24px;
      height: 24px;
      margin-bottom: 8px;
      border-radius: 999px;
      background: #17201b;
      color: #ffffff;
      font-size: 12px;
      font-weight: 800;
    }
    ul {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }
    code {
      display: block;
      max-width: 100%;
      padding: 11px;
      overflow-x: auto;
      border-radius: 8px;
      background: #17201b;
      color: #f7f9f6;
      font-size: 12px;
      line-height: 1.45;
      white-space: nowrap;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }
    .warning {
      border-left: 4px solid var(--danger);
    }
    .category-flow {
      display: grid;
      grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
      gap: 16px;
      align-items: center;
    }
    .focus-card {
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--rose-soft);
    }
    .focus-card span {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .focus-card strong {
      display: block;
      margin-top: 8px;
      font-size: 26px;
      line-height: 1.1;
    }
    .arc-panel {
      min-width: 0;
      overflow: hidden;
    }
    .arc-panel svg {
      display: block;
      width: 100%;
      height: auto;
    }
    .arc-label {
      font-size: 13px;
      font-weight: 700;
      fill: #17201b;
    }
    .arc-muted {
      font-size: 11px;
      fill: #64706c;
    }
    @media (max-width: 760px) {
      header, .hero-band, .grid, .metrics, .mode-grid, .pipeline, .category-flow { grid-template-columns: 1fr; }
      main { width: min(100% - 24px, 1100px); }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Email Vault Admin Console</h1>
        <p>Private owner area for moving from synthetic demos toward real Gmail preservation.</p>
      </div>
      <form method="post" action="/logout">
        <button type="submit">Log Out</button>
      </form>
    </header>
    <nav class="tabbar" aria-label="Admin sections">
      <a href="#overview">Overview</a>
      <a href="#modes">Modes</a>
      <a href="#categories">Categories</a>
      <a href="#readiness">Readiness</a>
      <a href="#commands">Commands</a>
    </nav>
    <section class="hero-band" id="overview">
      <div>
        <div class="brand-line">
          <span class="brand-mark">EV</span>
          <div>
            <strong>Personal inbox offloader and cleanup cockpit</strong>
            <p>Preserve useful mail outside Gmail first, then review what can leave the inbox.</p>
          </div>
        </div>
      </div>
      <div class="hero-stat">
        <span>Live Gmail</span>
        <strong>Locked</strong>
        <p>Read-only OAuth path is being prepared.</p>
      </div>
    </section>
    <div class="metrics">
      <div class="metric"><span>Session</span><strong>Admin</strong></div>
      <div class="metric"><span>Gmail OAuth</span><strong>__OAUTH_STATUS__</strong></div>
      <div class="metric"><span>Token Storage</span><strong>__TOKEN_STATUS__</strong></div>
    </div>
    <div class="grid">
      <section id="modes">
        <h2>Vault Modes</h2>
        <div class="mode-grid">
          <div class="mode-card">
            <strong>Preserve</strong>
            <span>Save portable copies without changing Gmail.</span>
          </div>
          <div class="mode-card clean">
            <strong>Clean Inbox</strong>
            <span>Review saved mail before labels or archive.</span>
          </div>
          <div class="mode-card free">
            <strong>Free Space</strong>
            <span>Deferred until delete review and recovery rules exist.</span>
          </div>
        </div>
      </section>
      <section>
        <h2>Safety Pipeline</h2>
        <div class="pipeline">
          <div class="step"><strong>Connect</strong><span>Read-only OAuth setup.</span></div>
          <div class="step"><strong>Preserve</strong><span>Export package and checksum.</span></div>
          <div class="step"><strong>Review</strong><span>Category and route decision.</span></div>
          <div class="step"><strong>Clean</strong><span>Mutation remains locked.</span></div>
        </div>
      </section>
      <section id="categories">
        <h2>Category Flow</h2>
        <div class="category-flow">
          <div class="focus-card">
            <span>Current strongest signal</span>
            <strong>__TOP_CATEGORY__</strong>
            <p>__CATEGORY_NOTE__</p>
          </div>
          <div class="arc-panel">
            __CATEGORY_ARC__
          </div>
        </div>
      </section>
      <section>
        <h2>Private Workflow</h2>
        <ul>
          <li>Use the demo page for synthetic review queue proof.</li>
          <li>Use the CLI for local verified export packages today.</li>
          <li>Add Gmail OAuth, encrypted token storage, and review controls before live sync.</li>
        </ul>
        <div class="actions">
          <a class="button" href="/demo">Open Synthetic Demo</a>
          <a class="button secondary" href="/demo/data">View Demo JSON</a>
        </div>
      </section>
      <section class="warning">
        <h2>Live Gmail Gate</h2>
        <p>Real Gmail connection stays blocked until a private Google OAuth project, HTTPS callback URL, token storage, and explicit cleanup review are configured.</p>
      </section>
      <section id="readiness">
        <h2>OAuth Readiness</h2>
        __MISSING_HTML__
        <div class="actions">
          __CONNECT_HTML__
          <a class="button secondary" href="__READINESS_JSON_LINK__">View OAuth Readiness JSON</a>
        </div>
      </section>
      <section>
        <h2>Requested Gmail Scopes</h2>
        __SCOPE_HTML__
        <p>__MUTATION_COPY__</p>
      </section>
      <section>
        <h2>Token Storage Readiness</h2>
        __TOKEN_MISSING_HTML__
        <p>Plaintext token storage remains disabled.</p>
        <div class="actions">
          <a class="button secondary" href="__TOKEN_READINESS_JSON_LINK__">View Token Storage JSON</a>
        </div>
      </section>
      <section>
        <h2>OAuth Callback Shell</h2>
        <p>The callback route is registered at <code>http://127.0.0.1:8000/oauth/google/callback</code></p>
        <p>Authorization codes are exchanged only after admin-session state validation and complete encrypted-storage config.</p>
      </section>
      <section id="commands">
        <h2>Local Preserve Command</h2>
        <code>python -m services.api.app.cli preserve-local --request tests/fixtures/emails/unknown_message.json --export-root .local/EmailVault --json</code>
      </section>
      <section>
        <h2>Synthetic Demo Command</h2>
        <code>python -m services.api.app.cli synthetic-demo --export-root .local/EmailVault --report-markdown .local/demo-report.md --json</code>
      </section>
    </div>
  </main>
</body>
</html>"""
    return (
        template.replace("__OAUTH_STATUS__", html.escape(oauth_status))
        .replace("__TOKEN_STATUS__", html.escape(token_status))
        .replace("__MISSING_HTML__", missing_html)
        .replace("__CONNECT_HTML__", connect_html)
        .replace("__READINESS_JSON_LINK__", readiness_json_link)
        .replace("__SCOPE_HTML__", scope_html)
        .replace("__MUTATION_COPY__", html.escape(mutation_copy))
        .replace("__TOKEN_MISSING_HTML__", token_missing_html)
        .replace("__TOKEN_READINESS_JSON_LINK__", token_readiness_json_link)
        .replace("__TOP_CATEGORY__", html.escape(category_flow["top_category"]))
        .replace("__CATEGORY_NOTE__", html.escape(category_flow["note"]))
        .replace("__CATEGORY_ARC__", category_flow["arc_html"])
    )


def _admin_category_flow() -> dict[str, str]:
    categories = (
        ("newsletter", 1, "#b6472f"),
        ("bank_financial", 1, "#365f91"),
        ("unknown", 1, "#256f5b"),
    )
    top_category = max(categories, key=lambda item: item[1])[0]
    note = "Synthetic demo data is tied today; the live view will start from the highest-volume category."
    arc_html = """
<svg viewBox="0 0 430 190" role="img" aria-label="Category flow starts from the strongest category">
  <path d="M48 142 C92 34, 196 22, 248 92 S340 162, 386 64" fill="none" stroke="#d7dfda" stroke-width="18" stroke-linecap="round"/>
  <path d="M48 142 C92 34, 196 22, 248 92" fill="none" stroke="#b6472f" stroke-width="18" stroke-linecap="round"/>
  <circle cx="48" cy="142" r="18" fill="#b6472f"/>
  <circle cx="248" cy="92" r="15" fill="#365f91"/>
  <circle cx="386" cy="64" r="15" fill="#256f5b"/>
  <text x="28" y="178" class="arc-label">newsletter</text>
  <text x="28" y="188" class="arc-muted">current top signal</text>
  <text x="206" y="70" class="arc-label">bank</text>
  <text x="206" y="84" class="arc-muted">review gate</text>
  <text x="330" y="42" class="arc-label">unknown</text>
  <text x="330" y="56" class="arc-muted">hold queue</text>
</svg>"""
    return {
        "top_category": top_category,
        "note": note,
        "arc_html": arc_html,
    }


def _render_oauth_callback_html(
    *,
    exchange_result: OAuthCallbackExchangeResult,
    code_present: bool,
    state_present: bool,
    oauth_readiness: GmailOAuthReadiness,
    token_storage_readiness: TokenStorageReadiness,
) -> str:
    checks = (
        ("OAuth config", oauth_readiness.configured),
        ("Token storage config", token_storage_readiness.configured),
        ("State parameter present", state_present),
        ("Authorization code present", code_present),
        ("Encrypted token stored", exchange_result.status == "stored"),
    )
    check_rows = "".join(
        f"<li>{html.escape(label)}: {'yes' if value else 'no'}</li>"
        for label, value in checks
    )
    summary_html = ""
    if exchange_result.token_summary:
        scopes = exchange_result.token_summary.get("scopes", [])
        scope_items = "".join(f"<li>{html.escape(str(scope))}</li>" for scope in scopes)
        summary_html = f"""
      <h2>Stored Token Summary</h2>
      <ul>
        <li>Provider: {html.escape(str(exchange_result.token_summary.get("provider", "")))}</li>
        <li>Owner: {html.escape(str(exchange_result.token_summary.get("owner_id", "")))}</li>
        <li>Refresh token present: {'yes' if exchange_result.token_summary.get("has_refresh_token") else 'no'}</li>
        <li>Expires at: {html.escape(str(exchange_result.token_summary.get("expires_at", "")))}</li>
      </ul>
      <h2>Stored Scopes</h2>
      <ul>{scope_items}</ul>"""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Email Vault OAuth Callback</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #16201d;
      --muted: #64706c;
      --line: #d8dfdc;
      --paper: #ffffff;
      --page: #edf2ef;
      --accent: #256f5b;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--page); color: var(--ink); }}
    main {{ width: min(860px, calc(100vw - 32px)); margin: 0 auto; padding: 36px 0; }}
    section {{ background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.15; letter-spacing: 0; }}
    p, li {{ color: var(--muted); font-size: 14px; line-height: 1.5; }}
    a.button {{ display: inline-flex; align-items: center; min-height: 38px; padding: 8px 12px; border-radius: 8px; background: var(--accent); color: #fff; font-weight: 700; text-decoration: none; }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>{html.escape(exchange_result.title)}</h1>
      <p>{html.escape(exchange_result.detail)}</p>
      <ul>{check_rows}</ul>
      {summary_html}
      <a class="button" href="/admin">Back To Admin</a>
    </section>
  </main>
</body>
</html>"""
