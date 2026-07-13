from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from services.api.app.domain.contracts import ApiError, ArchiveRecordReference, ArchiveState, ErrorCategory
from services.api.app.repositories.interfaces import AuditEvent


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS archive_records (
    record_id TEXT PRIMARY KEY,
    owner_subject TEXT NOT NULL,
    vault_thread_id TEXT NOT NULL,
    gmail_thread_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    snapshot_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (owner_subject, snapshot_sha256),
    UNIQUE (owner_subject, gmail_thread_id, revision)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    state TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (record_id) REFERENCES archive_records(record_id)
);
"""


class SqliteRevisionRepository:
    """SQLite implementation for local P2 persistence tests and demos.

    The database stores only server-generated identifiers and snapshot hashes.
    Email content, subjects, addresses, filenames, PDFs, attachments, and tokens
    do not belong in these tables.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(SCHEMA_SQL)

    def create_revision(
        self,
        owner_subject: str,
        gmail_thread_id: str,
        reference: ArchiveRecordReference,
    ) -> ArchiveRecordReference:
        try:
            with closing(self._connect()) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO archive_records (
                            record_id,
                            owner_subject,
                            vault_thread_id,
                            gmail_thread_id,
                            revision,
                            snapshot_sha256
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            reference.record_id,
                            owner_subject,
                            reference.vault_thread_id,
                            gmail_thread_id,
                            reference.revision,
                            reference.snapshot_sha256,
                        ),
                    )
        except sqlite3.IntegrityError as exc:
            raise ApiError(
                ErrorCategory.DUPLICATE_CONFLICT,
                "Archive revision conflicts with an existing snapshot or revision.",
                "archive_record",
            ) from exc
        return reference

    def find_by_snapshot_hash(self, owner_subject: str, snapshot_sha256: str) -> ArchiveRecordReference | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT vault_thread_id, revision, record_id, snapshot_sha256
                FROM archive_records
                WHERE owner_subject = ? AND snapshot_sha256 = ?
                """,
                (owner_subject, snapshot_sha256),
            ).fetchone()
        return self._reference_from_row(row) if row else None

    def next_revision_for_thread(self, owner_subject: str, gmail_thread_id: str) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(revision), 0) + 1 AS next_revision
                FROM archive_records
                WHERE owner_subject = ? AND gmail_thread_id = ?
                """,
                (owner_subject, gmail_thread_id),
            ).fetchone()
        return int(row["next_revision"])

    def append_audit_event(self, event: AuditEvent) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO audit_events (record_id, state, occurred_at)
                    VALUES (?, ?, ?)
                    """,
                    (event.record_id, event.state.value, event.occurred_at.isoformat()),
                )

    def list_audit_events(self, record_id: str) -> tuple[AuditEvent, ...]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT record_id, state, occurred_at
                FROM audit_events
                WHERE record_id = ?
                ORDER BY id
                """,
                (record_id,),
            ).fetchall()
        return tuple(
            AuditEvent(
                record_id=row["record_id"],
                state=ArchiveState(row["state"]),
                occurred_at=datetime.fromisoformat(row["occurred_at"]),
            )
            for row in rows
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _reference_from_row(row: sqlite3.Row) -> ArchiveRecordReference:
        return ArchiveRecordReference(
            vault_thread_id=row["vault_thread_id"],
            revision=int(row["revision"]),
            record_id=row["record_id"],
            snapshot_sha256=row["snapshot_sha256"],
        )
