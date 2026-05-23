"""Integration tests for share link feature (todos #5.3, #5.4)."""
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiaryEntry, QnASession, ShareLink
from sqlalchemy import select


async def _login(client):
    await client.post("/api/login", json={"password": "inha-nxt"})


async def _make_diary(db: AsyncSession, user_id: int, diary_date: date) -> None:
    session = QnASession(user_id=user_id, diary_date=diary_date, status="completed")
    db.add(session)
    await db.flush()
    entry = DiaryEntry(
        session_id=session.id,
        user_id=user_id,
        diary_date=diary_date,
        body="오늘의 일기 내용입니다.",
        summary="요약",
        emotion="happy",
    )
    db.add(entry)
    await db.flush()


@pytest.mark.asyncio
async def test_share_create_returns_token(client, db_session, pg_container):
    """POST /api/diary/{date}/share returns token and url."""
    await _login(client)
    await _make_diary(db_session, 1, date(2045, 1, 1))
    await db_session.commit()

    resp = await client.post("/api/diary/2045-01-01/share")
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["url"].startswith("/share/")
    assert data["expires_at"]


@pytest.mark.asyncio
async def test_share_no_diary_returns_404(client, db_session, pg_container):
    """POST /api/diary/{date}/share returns 404 when diary doesn't exist."""
    await _login(client)
    resp = await client.post("/api/diary/2099-12-31/share")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_share_idempotent(client, db_session, pg_container):
    """Second POST returns same token (idempotent)."""
    await _login(client)
    await _make_diary(db_session, 1, date(2045, 2, 1))
    await db_session.commit()

    resp1 = await client.post("/api/diary/2045-02-01/share")
    resp2 = await client.post("/api/diary/2045-02-01/share")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["token"] == resp2.json()["token"]
