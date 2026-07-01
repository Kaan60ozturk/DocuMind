"""SQLite-backed document registry: metadata only, no ORM.

A connection is opened per operation — dead simple and thread-safe, and the
registry sees a handful of operations per user action at most.
"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    pages       INTEGER NOT NULL,
    chunks      INTEGER NOT NULL,
    size_bytes  INTEGER NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    filename: str
    pages: int
    chunks: int
    size_bytes: int
    status: str
    created_at: str


class DocumentRegistry:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, record: DocumentRecord) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO documents (id, filename, pages, chunks, size_bytes, status,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.filename,
                    record.pages,
                    record.chunks,
                    record.size_bytes,
                    record.status,
                    record.created_at,
                ),
            )
            conn.commit()

    def get(self, doc_id: str) -> DocumentRecord | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return DocumentRecord(**dict(row)) if row else None

    def list(self) -> list[DocumentRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [DocumentRecord(**dict(row)) for row in rows]

    def delete(self, doc_id: str) -> bool:
        with closing(self._connect()) as conn:
            cursor = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
        return cursor.rowcount > 0
