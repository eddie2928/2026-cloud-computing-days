import json
from pathlib import Path

import aiosqlite

from agentbox.models import PromptEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id                    TEXT PRIMARY KEY,
  created_at            TEXT NOT NULL,
  resolved_at           TEXT,
  source                TEXT NOT NULL,
  method                TEXT NOT NULL,
  url                   TEXT NOT NULL,
  request_headers_json  TEXT NOT NULL,
  request_body          TEXT,
  prompt_excerpt        TEXT,
  status                TEXT NOT NULL,
  verdict_by            TEXT,
  upstream_status_code  INTEGER,
  error                 TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_status_created ON events(status, created_at DESC);
"""


async def init_db(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def insert_event(db_path: str | Path, event: PromptEvent) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO events
               (id, created_at, resolved_at, source, method, url,
                request_headers_json, request_body, prompt_excerpt,
                status, verdict_by, upstream_status_code, error)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event.id,
                event.created_at.isoformat(),
                event.resolved_at.isoformat() if event.resolved_at else None,
                event.source,
                event.method,
                str(event.url),
                json.dumps(event.request_headers),
                event.request_body,
                event.prompt_excerpt,
                event.status,
                event.verdict_by,
                event.upstream_status_code,
                event.error,
            ),
        )
        await db.commit()


async def update_verdict(
    db_path: str | Path,
    event_id: str,
    *,
    status: str,
    verdict_by: str = "user",
    resolved_at: str,
    upstream_status_code: int | None = None,
    error: str | None = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE events SET status=?, verdict_by=?, resolved_at=?,
               upstream_status_code=?, error=? WHERE id=?""",
            (status, verdict_by, resolved_at, upstream_status_code, error, event_id),
        )
        await db.commit()


async def get_event(db_path: str | Path, event_id: str) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM events WHERE id=?", (event_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_events(
    db_path: str | Path,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if status:
            async with db.execute(
                "SELECT * FROM events WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]
