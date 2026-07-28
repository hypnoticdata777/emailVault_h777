from __future__ import annotations

import hashlib
import hmac
import html
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

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

    return HTMLResponse(_render_admin_html())


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


def _render_admin_html() -> str:
    return """<!doctype html>
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
      header, .grid, .metrics { grid-template-columns: 1fr; }
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
    <div class="metrics">
      <div class="metric"><span>Session</span><strong>Admin</strong></div>
      <div class="metric"><span>Gmail OAuth</span><strong>Not connected</strong></div>
      <div class="metric"><span>Mailbox mutation</span><strong>Disabled</strong></div>
    </div>
    <div class="grid">
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
