from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from services.api.app.auth.identity import GoogleIdentity
from services.api.app.core.settings import load_settings
from services.api.app.domain.contracts import (
    ApiError,
    ArchivePreferences,
    ArchiveThreadRequest,
    AttachmentDescriptor,
    BodyRepresentation,
    ClientContext,
    ErrorCategory,
    MessageHeader,
    MessageSnapshot,
    Participant,
    ThreadSnapshot,
)
from services.api.app.domain.export_package import ExportFolderLayout
from services.api.app.repositories.sqlite import SqliteRevisionRepository, sqlite_path_from_database_url
from services.api.app.services.archive import ArchiveCoordinator, LocalPreservePackageOutcome
from services.api.app.services.storage.attachments import MappingAttachmentContentProvider, NullAttachmentContentProvider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Email Vault local maintenance commands.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="Create or update the configured local SQLite schema.")

    preserve = subcommands.add_parser(
        "preserve-local",
        help="Run local Preserve Mode for one archive request JSON file.",
    )
    preserve.add_argument("--request", required=True, type=Path, help="Path to an ArchiveThreadRequest JSON file.")
    preserve.add_argument("--export-root", required=True, type=Path, help="Folder where Email Vault packages are written.")
    preserve.add_argument("--database-url", help="SQLite URL for local archive state. Defaults to configured DATABASE_URL.")
    preserve.add_argument("--identity-subject", default="local-demo-subject", help="Synthetic local owner subject.")
    preserve.add_argument("--identity-email", default="owner@example.com", help="Synthetic local owner email.")
    preserve.add_argument(
        "--layout",
        choices=[item.value for item in ExportFolderLayout],
        default=ExportFolderLayout.DOMAIN_FIRST.value,
        help="Folder layout for the local package route.",
    )
    preserve.add_argument("--sender-domain-override", help="Optional user-controlled sender-domain route override.")
    preserve.add_argument(
        "--attachment-content",
        action="append",
        default=(),
        metavar="MESSAGE_ID:ATTACHMENT_ID=PATH",
        help="Trusted attachment bytes to include in the export package. Repeat for multiple attachments.",
    )
    preserve.add_argument("--json", action="store_true", help="Print the result as JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init-db":
        settings = load_settings()
        database_path = sqlite_path_from_database_url(settings.database_url)
        # The repository constructor runs the idempotent schema bootstrap. This
        # command is intentionally tiny so local setup and future migrations have
        # one obvious entry point.
        SqliteRevisionRepository(database_path)
        print(f"Initialized Email Vault SQLite database at {database_path}")
        return 0
    if args.command == "preserve-local":
        try:
            outcome = _preserve_local(args)
        except ApiError as exc:
            print(f"Email Vault error: {exc.category.value}: {exc.message}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(_outcome_payload(outcome), sort_keys=True, indent=2))
        else:
            _print_local_preserve_summary(outcome)
        return 0
    return 1


def _preserve_local(args: argparse.Namespace) -> LocalPreservePackageOutcome:
    settings = load_settings()
    database_path = sqlite_path_from_database_url(args.database_url or settings.database_url)
    repository = SqliteRevisionRepository(database_path)
    request = _load_archive_request(args.request)
    identity = GoogleIdentity(
        subject=args.identity_subject,
        email=args.identity_email,
        email_verified=True,
    )
    provider = _attachment_provider(args.attachment_content)
    return ArchiveCoordinator(repository).preserve_export_package_with_details(
        request,
        identity,
        export_root=args.export_root,
        attachment_content_provider=provider,
        layout=ExportFolderLayout(args.layout),
        sender_domain_override=args.sender_domain_override,
    )


def _load_archive_request(path: Path) -> ArchiveThreadRequest:
    raw = json.loads(path.read_text(encoding="utf-8"))
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


def _attachment_provider(values: tuple[str, ...]) -> MappingAttachmentContentProvider | NullAttachmentContentProvider:
    content_by_source: dict[tuple[str, str], bytes] = {}
    for value in values:
        source, separator, path_text = value.partition("=")
        message_id, source_separator, attachment_id = source.partition(":")
        if not separator or not source_separator or not message_id or not attachment_id or not path_text:
            raise ApiError(
                ErrorCategory.INVALID_SCHEMA,
                "Attachment content must use MESSAGE_ID:ATTACHMENT_ID=PATH.",
                "attachment_content",
            )
        content_by_source[(message_id, attachment_id)] = Path(path_text).read_bytes()
    if not content_by_source:
        return NullAttachmentContentProvider()
    return MappingAttachmentContentProvider(content_by_source)


def _outcome_payload(outcome: LocalPreservePackageOutcome) -> dict[str, Any]:
    result = outcome.result
    record = result.record
    verification = result.verification
    return {
        "status": result.status.value,
        "record_id": record.record_id if record else None,
        "vault_thread_id": record.vault_thread_id if record else None,
        "revision": record.revision if record else None,
        "snapshot_sha256": record.snapshot_sha256 if record else None,
        "package_path": str(outcome.package_path) if outcome.package_path else None,
        "relative_package_path": outcome.relative_package_path,
        "verified": verification.verified if verification else None,
        "artifact_count": verification.artifact_count if verification else None,
        "total_bytes": verification.total_bytes if verification else None,
        "gmail_finalization_enabled": result.gmail_finalization.enabled,
    }


def _print_local_preserve_summary(outcome: LocalPreservePackageOutcome) -> None:
    payload = _outcome_payload(outcome)
    print("Email Vault local Preserve Mode")
    print(f"Status: {payload['status']}")
    print(f"Record ID: {payload['record_id']}")
    print(f"Revision: {payload['revision']}")
    print(f"Package path: {payload['package_path']}")
    print(f"Relative package path: {payload['relative_package_path']}")
    print(f"Verified: {payload['verified']}")
    print(f"Artifact count: {payload['artifact_count']}")
    print(f"Total bytes: {payload['total_bytes']}")
    print(f"Gmail finalization enabled: {payload['gmail_finalization_enabled']}")


if __name__ == "__main__":
    raise SystemExit(main())
