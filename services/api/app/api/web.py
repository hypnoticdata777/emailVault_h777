from __future__ import annotations

import hashlib
import hmac
import html
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from services.api.app.auth.oauth_readiness import GmailOAuthReadiness, inspect_gmail_oauth_readiness
from services.api.app.auth.token_storage import TokenStorageReadiness, inspect_token_storage_readiness
from services.api.app.core.settings import load_settings


router = APIRouter()

SESSION_COOKIE = "email_vault_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60


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
    return HTMLResponse(
        _render_admin_html(
            inspect_gmail_oauth_readiness(settings),
            inspect_token_storage_readiness(settings),
        )
    )


@router.get("/admin/gmail/oauth/readiness")
async def gmail_oauth_readiness(request: Request) -> Response | dict[str, object]:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    return inspect_gmail_oauth_readiness(load_settings()).to_dict()


@router.get("/admin/gmail/token-storage/readiness")
async def gmail_token_storage_readiness(request: Request) -> Response | dict[str, object]:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    return inspect_token_storage_readiness(load_settings()).to_dict()


@router.get("/oauth/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(request: Request) -> Response:
    if _session_role(request) != "admin":
        return RedirectResponse("/login", status_code=303)

    settings = load_settings()
    return HTMLResponse(
        _render_oauth_callback_html(
            error=request.query_params.get("error", ""),
            code_present=bool(request.query_params.get("code", "")),
            state_present=bool(request.query_params.get("state", "")),
            oauth_readiness=inspect_gmail_oauth_readiness(settings),
            token_storage_readiness=inspect_token_storage_readiness(settings),
        )
    )


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


def _render_login_html(message: str = "") -> str:
    safe_message = html.escape(message)
    message_html = f'<p class="notice">{safe_message}</p>' if safe_message else ""
    template = """<!doctype html>
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


def _render_admin_html(readiness: GmailOAuthReadiness, token_storage: TokenStorageReadiness) -> str:
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
        else "<p>Token storage config is present. Token exchange is still not enabled.</p>"
    )
    token_readiness_json_link = "/admin/gmail/token-storage/readiness"
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
    @media (max-width: 760px) {
      header, .hero-band, .grid, .metrics, .mode-grid, .pipeline { grid-template-columns: 1fr; }
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
    <section class="hero-band">
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
      <section>
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
      <section>
        <h2>OAuth Readiness</h2>
        __MISSING_HTML__
        <div class="actions">
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
        <p>Authorization codes are not stored until token exchange and encrypted storage are implemented.</p>
      </section>
      <section>
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
        .replace("__READINESS_JSON_LINK__", readiness_json_link)
        .replace("__SCOPE_HTML__", scope_html)
        .replace("__MUTATION_COPY__", html.escape(mutation_copy))
        .replace("__TOKEN_MISSING_HTML__", token_missing_html)
        .replace("__TOKEN_READINESS_JSON_LINK__", token_readiness_json_link)
    )


def _render_oauth_callback_html(
    *,
    error: str,
    code_present: bool,
    state_present: bool,
    oauth_readiness: GmailOAuthReadiness,
    token_storage_readiness: TokenStorageReadiness,
) -> str:
    if error:
        title = "OAuth Callback Error"
        detail = f"Google returned an OAuth error: {html.escape(error)}."
    elif code_present:
        title = "OAuth Callback Received"
        detail = "Authorization code was received and deliberately discarded because token exchange is not enabled yet."
    else:
        title = "OAuth Callback Ready"
        detail = "Callback route is reachable. No authorization code was supplied."

    checks = (
        ("OAuth config", oauth_readiness.configured),
        ("Token storage config", token_storage_readiness.configured),
        ("State parameter present", state_present),
        ("Authorization code present", code_present),
    )
    check_rows = "".join(
        f"<li>{html.escape(label)}: {'yes' if value else 'no'}</li>"
        for label, value in checks
    )
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
      <h1>{html.escape(title)}</h1>
      <p>{detail}</p>
      <ul>{check_rows}</ul>
      <a class="button" href="/admin">Back To Admin</a>
    </section>
  </main>
</body>
</html>"""
