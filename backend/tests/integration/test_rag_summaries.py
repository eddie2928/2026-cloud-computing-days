"""Integration tests for _get_recent_summaries (todo #13.1).

Uses 2030+ dates to avoid interference with committed entries from other test runs.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiaryEntry, QnASession
from app.routers.qna import _get_recent_summaries


async def _make_diary(db: AsyncSession, user_id: int, diary_date: date, summary: str) -> None:
    session = QnASession(user_id=user_id, diary_date=diary_date, status="completed")
    db.add(session)
    await db.flush()
    entry = DiaryEntry(
        session_id=session.id,
        user_id=user_id,
        diary_date=diary_date,
        body="본문",
        summary=summary,
        emotion="neutral",
    )
    db.add(entry)
    await db.flush()


@pytest.mark.asyncio
async def test_one_day_ago_included(db_session, pg_container):
    """A diary from 1 day before diary_date is included."""
    today = date(2030, 1, 2)
    yesterday = today - timedelta(days=1)
    user_id = 1
    await _make_diary(db_session, user_id, yesterday, "어제 요약")
    await db_session.flush()

    results = await _get_recent_summaries(db_session, user_id, today)
    dates = [r[0] for r in results]
    assert yesterday in dates


@pytest.mark.asyncio
async def test_31_days_ago_excluded(db_session, pg_container):
    """A diary from 31 days before diary_date is excluded."""
    today = date(2030, 2, 2)
    old_date = today - timedelta(days=31)
    user_id = 1
    await _make_diary(db_session, user_id, old_date, "오래된 요약")
    await db_session.flush()

    results = await _get_recent_summaries(db_session, user_id, today)
    dates = [r[0] for r in results]
    assert old_date not in dates


@pytest.mark.asyncio
async def test_same_day_excluded(db_session, pg_container):
    """A diary with the same date as diary_date is excluded."""
    today = date(2030, 3, 1)
    user_id = 1
    await _make_diary(db_session, user_id, today, "오늘 요약")
    await db_session.flush()

    results = await _get_recent_summaries(db_session, user_id, today)
    dates = [r[0] for r in results]
    assert today not in dates


@pytest.mark.asyncio
async def test_empty_when_no_diaries(db_session, pg_container):
    """Returns empty list when no diary entries exist in range."""
    today = date(2030, 4, 1)
    user_id = 1
    results = await _get_recent_summaries(db_session, user_id, today)
    assert results == []
