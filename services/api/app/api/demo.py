from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

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
from services.api.app.domain.export_package import ExportFolderLayout, ExportPackageMode
from services.api.app.services.export_dry_run import ExportDryRunPlan, plan_export_dry_run


router = APIRouter()

SYNTHETIC_DEMO_FIXTURES = ("newsletter_digest", "bank_notice", "unknown_message")


@router.get("/demo", response_class=HTMLResponse)
async def synthetic_demo_page() -> HTMLResponse:
    return HTMLResponse(_render_demo_html(_synthetic_demo_payload()))


@router.get("/demo/data")
async def synthetic_demo_data() -> dict[str, Any]:
    return _synthetic_demo_payload()


def _synthetic_demo_payload() -> dict[str, Any]:
    requests = tuple(_load_fixture(name) for name in SYNTHETIC_DEMO_FIXTURES)
    plan = plan_export_dry_run(
        (request.thread for request in requests),
        mode=ExportPackageMode.CLEAN_INBOX,
        layout=ExportFolderLayout.DOMAIN_FIRST,
        mark_read=True,
        archive=True,
    )
    return {
        "mode": "synthetic_web_demo",
        "gmail_mutation_enabled": False,
        "writes_files": False,
        "report_command": (
            "python -m services.api.app.cli synthetic-demo --export-root .local/EmailVault "
            "--report-markdown .local/demo-report.md --json"
        ),
        "summary": _summary_payload(plan),
        "items": [_item_payload(item) for item in plan.items],
    }


def _summary_payload(plan: ExportDryRunPlan) -> dict[str, Any]:
    return {
        "total_threads": plan.summary.total_threads,
        "review_required_count": plan.summary.review_required_count,
        "approvable_count": plan.summary.total_threads - plan.summary.review_required_count,
        "by_category": plan.summary.by_category,
        "by_gmail_action": plan.summary.by_gmail_action,
        "by_export_path": plan.summary.by_export_path,
    }


def _item_payload(item) -> dict[str, Any]:
    return {
        "subject": item.subject,
        "category": item.category,
        "sender_domain": item.sender_domain,
        "export_path": item.export_path,
        "planned_gmail_action": item.planned_gmail_action.value,
        "review_required": item.review_required,
        "intent_policy": "eligible" if not item.review_required else "held_for_review",
        "evidence": [{"reason": evidence.reason, "detail": evidence.detail} for evidence in item.evidence],
    }


def _render_demo_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    item_rows = "\n".join(_item_row(item) for item in payload["items"])
    category_rows = "\n".join(_count_row(category, count) for category, count in summary["by_category"].items())
    action_rows = "\n".join(_count_row(action, count) for action, count in summary["by_gmail_action"].items())
    command = html.escape(payload["report_command"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Email Vault Synthetic Demo</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17201b;
      --muted: #667069;
      --line: #d9dfd8;
      --panel: #f7f9f6;
      --paper: #ffffff;
      --accent: #256f5b;
      --accent-2: #b6472f;
      --accent-3: #365f91;
      --warn-bg: #fff3e4;
      --ok-bg: #e8f5ef;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #eef2ec;
      color: var(--ink);
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 36px;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 20px;
      align-items: end;
      padding: 18px 0 22px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{
      margin: 0;
      font-size: 30px;
      line-height: 1.15;
      font-weight: 760;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 17px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    .subhead {{
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
      max-width: 760px;
    }}
    .status-strip {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      border: 1px solid var(--line);
      background: var(--paper);
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 13px;
      color: var(--ink);
      white-space: nowrap;
    }}
    .dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
      flex: 0 0 auto;
    }}
    .dot.warn {{ background: var(--accent-2); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric, .panel {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{
      padding: 14px;
      min-height: 92px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .metric strong {{
      display: block;
      margin-top: 9px;
      font-size: 27px;
      line-height: 1;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.7fr 1fr;
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      padding: 16px;
      overflow: hidden;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th {{
      text-align: left;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
    }}
    td {{
      padding: 12px 8px;
      border-bottom: 1px solid #edf0ec;
      vertical-align: middle;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    code {{
      display: block;
      padding: 11px;
      overflow-x: auto;
      border-radius: 8px;
      background: #17201b;
      color: #f7f9f6;
      font-size: 12px;
      line-height: 1.45;
      white-space: nowrap;
    }}
    .tag {{
      display: inline-flex;
      border-radius: 999px;
      padding: 5px 8px;
      font-size: 12px;
      background: var(--ok-bg);
      color: #195441;
      white-space: nowrap;
    }}
    .tag.review {{
      background: var(--warn-bg);
      color: #914020;
    }}
    .counts {{
      display: grid;
      gap: 12px;
    }}
    .count-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 42px;
      gap: 10px;
      align-items: center;
      font-size: 13px;
    }}
    .bar {{
      height: 9px;
      border-radius: 999px;
      background: #e6ebe5;
      overflow: hidden;
      margin-top: 6px;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: var(--accent-3);
      width: var(--w);
    }}
    .muted {{ color: var(--muted); }}
    @media (max-width: 860px) {{
      header, .grid {{ grid-template-columns: 1fr; }}
      .status-strip {{ justify-content: flex-start; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 560px) {{
      main {{ width: min(100vw - 20px, 1180px); padding-top: 12px; }}
      .metrics {{ grid-template-columns: 1fr; }}
      table {{ min-width: 720px; }}
      .panel.table-panel {{ overflow-x: auto; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Email Vault Synthetic Demo</h1>
        <p class="subhead">Canonical local preview for preserving useful email first, then reviewing cleanup intent. No Gmail account is connected here.</p>
      </div>
      <div class="status-strip">
        <span class="pill"><span class="dot"></span>Synthetic data</span>
        <span class="pill"><span class="dot"></span>No file writes</span>
        <span class="pill"><span class="dot warn"></span>Gmail mutation disabled</span>
      </div>
    </header>

    <section class="metrics" aria-label="Demo summary">
      <div class="metric"><span>Threads</span><strong>{summary["total_threads"]}</strong></div>
      <div class="metric"><span>Needs review</span><strong>{summary["review_required_count"]}</strong></div>
      <div class="metric"><span>Approvable</span><strong>{summary["approvable_count"]}</strong></div>
      <div class="metric"><span>Gmail changes</span><strong>0</strong></div>
    </section>

    <section class="grid">
      <div class="panel table-panel">
        <h2>Review Queue</h2>
        <table>
          <thead>
            <tr>
              <th>Subject</th>
              <th>Category</th>
              <th>Route</th>
              <th>Planned action</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {item_rows}
          </tbody>
        </table>
      </div>

      <div class="counts">
        <div class="panel">
          <h2>Categories</h2>
          {category_rows}
        </div>
        <div class="panel">
          <h2>Planned Gmail Actions</h2>
          {action_rows}
        </div>
        <div class="panel">
          <h2>Demo Command</h2>
          <code>{command}</code>
        </div>
      </div>
    </section>
  </main>
</body>
</html>"""


def _item_row(item: dict[str, Any]) -> str:
    status = "Needs review" if item["review_required"] else "Approvable"
    tag_class = "tag review" if item["review_required"] else "tag"
    return (
        "<tr>"
        f"<td>{_e(item['subject'])}</td>"
        f"<td><span class=\"tag\">{_e(item['category'])}</span></td>"
        f"<td><span class=\"muted\">{_e(item['export_path'])}</span></td>"
        f"<td>{_e(item['planned_gmail_action'])}</td>"
        f"<td><span class=\"{tag_class}\">{status}</span></td>"
        "</tr>"
    )


def _count_row(label: str, count: int) -> str:
    width = max(12, min(100, count * 34))
    return (
        "<div class=\"count-row\">"
        f"<div>{_e(label)}<div class=\"bar\"><span style=\"--w: {width}%\"></span></div></div>"
        f"<strong>{count}</strong>"
        "</div>"
    )


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _load_fixture(name: str) -> ArchiveThreadRequest:
    raw = json.loads((_fixture_root() / f"{name}.json").read_text(encoding="utf-8"))
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


def _message(raw: dict[str, Any]) -> MessageSnapshot:
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
        headers=tuple(MessageHeader(name=item["name"], value=item.get("value", "")) for item in raw.get("headers", [])),
        bodies=tuple(BodyRepresentation(**item) for item in raw.get("bodies", [])),
        attachments=tuple(AttachmentDescriptor(**item) for item in raw.get("attachments", [])),
    )


def _participant(raw: dict[str, Any]) -> Participant:
    return Participant(email=raw["email"], display_name=raw.get("display_name"))


def _fixture_root() -> Path:
    return Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "emails"
