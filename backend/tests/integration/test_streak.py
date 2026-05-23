"""Integration tests for GET /api/user/streak (todo #1.2).

Uses far-future dates to avoid cross-test contamination.
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiaryEntry, QnASession


async def _login(client):
    await client.post("/api/login", json={"password": "inha-nxt"})


async def _make_entry(db: AsyncSession, user_id: int, diary_date: date) -> None:
    session = QnASession(user_id=user_id, diary_date=diary_date, status="completed")
    db.add(session)
    await db.flush()
    entry = DiaryEntry(
        session_id=session.id,
        user_id=user_id,
        diary_date=diary_date,
        body="본문",
        summary="요약",
        emotion="neutral",
    )
    db.add(entry)
    await db.flush()


@pytest.mark.asyncio
async def test_streak_zero_no_diary(client, db_session, pg_container):
    """Streak is 0 when no diary entries exist for the reference date."""
    await _login(client)
    with patch("app.routers.user.date") as mock_date:
        mock_date.today.return_value = date(2035, 1, 1)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        resp = await client.get("/api/user/streak")
    assert resp.status_code == 200
    assert resp.json()["streak"] == 0


@pytest.mark.asyncio
async def test_streak_one_consecutive(client, db_session, pg_container):
    """Streak is 1 when only today's diary exists."""
    await _login(client)
    today = date(2035, 2, 1)
    await _make_entry(db_session, 1, today)
    await db_session.commit()

    with patch("app.routers.user.date") as mock_date:
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        resp = await client.get("/api/user/streak")
    assert resp.status_code == 200
    assert resp.json()["streak"] == 1


@pytest.mark.asyncio
async def test_streak_two_consecutive(client, db_session, pg_container):
    """Streak is 2 when today and yesterday both have diaries."""
    await _login(client)
    today = date(2035, 3, 5)
    yesterday = today - timedelta(days=1)
    await _make_entry(db_session, 1, today)
    await _make_entry(db_session, 1, yesterday)
    await db_session.commit()

    with patch("app.routers.user.date") as mock_date:
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        resp = await client.get("/api/user/streak")
    assert resp.status_code == 200
    assert resp.json()["streak"] == 2


@pytest.mark.asyncio
async def test_streak_month_boundary(client, db_session, pg_container):
    """Streak correctly counts across month boundary (Jan 31 + Feb 1)."""
    await _login(client)
    feb1 = date(2035, 4, 1)
    jan31 = feb1 - timedelta(days=1)
    await _make_entry(db_session, 1, feb1)
    await _make_entry(db_session, 1, jan31)
    await db_session.commit()

    with patch("app.routers.user.date") as mock_date:
        mock_date.today.return_value = feb1
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        resp = await client.get("/api/user/streak")
    assert resp.status_code == 200
    assert resp.json()["streak"] == 2
