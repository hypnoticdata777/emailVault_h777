from __future__ import annotations

import argparse

from services.api.app.core.settings import load_settings
from services.api.app.repositories.sqlite import SqliteRevisionRepository, sqlite_path_from_database_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Email Vault local maintenance commands.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="Create or update the configured local SQLite schema.")
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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
