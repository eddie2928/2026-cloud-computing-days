"""Integration tests for GET /api/diary/search?q= (todo #2.2).

Uses far-future dates to avoid cross-test contamination.
"""
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiaryEntry, QnASession


async def _login(client):
    await client.post("/api/login", json={"password": "inha-nxt"})


async def _make_entry(db: AsyncSession, user_id: int, diary_date: date, body: str) -> None:
    session = QnASession(user_id=user_id, diary_date=diary_date, status="completed")
    db.add(session)
    await db.flush()
    entry = DiaryEntry(
        session_id=session.id,
        user_id=user_id,
        diary_date=diary_date,
        body=body,
        summary="요약",
        emotion="neutral",
    )
    db.add(entry)
    await db.flush()


@pytest.mark.asyncio
async def test_search_empty_q(client, db_session, pg_container):
    """Empty q returns empty results."""
    await _login(client)
    resp = await client.get("/api/diary/search?q=")
    assert resp.status_code == 200
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_search_no_match(client, db_session, pg_container):
    """q with no matching entries returns empty results."""
    await _login(client)
    await _make_entry(db_session, 1, date(2040, 1, 1), "오늘은 날씨가 맑았다")
    await db_session.commit()

    resp = await client.get("/api/diary/search?q=존재하지않는텍스트XYZ")
    assert resp.status_code == 200
    assert resp.json()["results"] == []


@pytest.mark.asyncio
async def test_search_match_with_snippet(client, db_session, pg_container):
    """q matching body returns result with snippet and emotion."""
    await _login(client)
    body = "오늘은 날씨가 매우 맑고 기분이 좋았다. 공원에서 산책을 했다."
    await _make_entry(db_session, 1, date(2040, 2, 1), body)
    await db_session.commit()

    resp = await client.get("/api/diary/search?q=산책")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) >= 1
    item = data["results"][0]
    assert "산책" in item["snippet"]
    assert len(item["snippet"]) <= 60
    assert item["emotion"] == "neutral"
    assert item["date"] == "2040-02-01"
