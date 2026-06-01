import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")

from unittest.mock import AsyncMock, MagicMock
import pytest
from mcp_server.tests.conftest import make_user, make_profile


# ── list_users ──────────────────────────────────────────────────────────────

async def test_list_users_empty(session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import list_users
    result = await list_users(session)
    assert result == {"status": "ok", "data": []}


async def test_list_users_returns_user_with_profile(session):
    profile = make_profile(nickname="Alice", gender="female", age=30,
                           occupation="engineer", hobbies=["reading"],
                           interests=["AI"])
    user = make_user(id=1, display_name="Alice", profile=profile)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [user]
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import list_users
    result = await list_users(session)
    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    d = result["data"][0]
    assert d["user_id"] == 1
    assert d["display_name"] == "Alice"
    assert d["profile"]["nickname"] == "Alice"
    assert d["profile"]["age"] == 30


async def test_list_users_null_profile(session):
    user = make_user(id=2, display_name="Bob", profile=None)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [user]
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import list_users
    result = await list_users(session)
    assert result["data"][0]["profile"] is None


# ── get_user_info ────────────────────────────────────────────────────────────

async def test_get_user_info_not_found(session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_user_info
    result = await get_user_info(session, 999)
    assert result == {
        "status": "error",
        "code": "USER_NOT_FOUND",
        "message": "No user with id=999",
    }


async def test_get_user_info_no_profile(session):
    user = make_user(id=1, display_name="Carol", profile=None)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_user_info
    result = await get_user_info(session, 1)
    assert result["status"] == "ok"
    assert result["data"]["profile"] is None
    assert result["data"]["display_name"] == "Carol"


async def test_get_user_info_with_profile(session):
    profile = make_profile(nickname="Carol", gender="other", age=28)
    user = make_user(id=1, display_name="Carol", profile=profile)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_user_info
    result = await get_user_info(session, 1)
    assert result["status"] == "ok"
    assert result["data"]["profile"]["nickname"] == "Carol"


# ── list_diaries ──────────────────────────────────────────────────────────────

def make_diary(diary_date="2026-01-15", emotion="happy", summary="Good day",
               created_at=None):
    from datetime import date, datetime, timezone
    e = MagicMock()
    e.diary_date = date.fromisoformat(diary_date)
    e.emotion = emotion
    e.summary = summary
    e.created_at = created_at or datetime(2026, 1, 15, tzinfo=timezone.utc)
    return e


async def test_list_diaries_invalid_date_from(session):
    from mcp_server.tools import list_diaries
    result = await list_diaries(session, 1, "bad-date", "2026-01-31")
    assert result == {
        "status": "error",
        "code": "INVALID_DATE",
        "message": "date_from and date_to must be YYYY-MM-DD",
    }


async def test_list_diaries_invalid_date_to(session):
    from mcp_server.tools import list_diaries
    result = await list_diaries(session, 1, "2026-01-01", "not-a-date")
    assert result["code"] == "INVALID_DATE"


async def test_list_diaries_user_not_found(session):
    session.get = AsyncMock(return_value=None)
    from mcp_server.tools import list_diaries
    result = await list_diaries(session, 99, "2026-01-01", "2026-01-31")
    assert result == {
        "status": "error",
        "code": "USER_NOT_FOUND",
        "message": "No user with id=99",
    }


async def test_list_diaries_returns_entries(session):
    session.get = AsyncMock(return_value=make_user())
    diary = make_diary(diary_date="2026-01-15", emotion="happy", summary="Good day")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [diary]
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import list_diaries
    result = await list_diaries(session, 1, "2026-01-01", "2026-01-31")
    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["diary_date"] == "2026-01-15"
    assert result["data"][0]["emotion"] == "happy"
    assert result["data"][0]["summary"] == "Good day"


async def test_list_diaries_empty_range(session):
    session.get = AsyncMock(return_value=make_user())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import list_diaries
    result = await list_diaries(session, 1, "2026-01-01", "2026-01-31")
    assert result == {"status": "ok", "data": []}


# ── get_emotion_trend ─────────────────────────────────────────────────────────

async def test_get_emotion_trend_invalid_date(session):
    from mcp_server.tools import get_emotion_trend
    result = await get_emotion_trend(session, 1, "2026-01-01", "oops")
    assert result["code"] == "INVALID_DATE"


async def test_get_emotion_trend_user_not_found(session):
    session.get = AsyncMock(return_value=None)
    from mcp_server.tools import get_emotion_trend
    result = await get_emotion_trend(session, 99, "2026-01-01", "2026-01-31")
    assert result["code"] == "USER_NOT_FOUND"


async def test_get_emotion_trend_returns_trend(session):
    from datetime import date
    session.get = AsyncMock(return_value=make_user())

    row1 = MagicMock()
    row1.diary_date = date(2026, 1, 1)
    row1.emotion = "happy"
    row2 = MagicMock()
    row2.diary_date = date(2026, 1, 2)
    row2.emotion = "sad"

    mock_result = MagicMock()
    mock_result.all.return_value = [row1, row2]
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_emotion_trend
    result = await get_emotion_trend(session, 1, "2026-01-01", "2026-01-31")
    assert result["status"] == "ok"
    assert result["data"] == [
        {"diary_date": "2026-01-01", "emotion": "happy"},
        {"diary_date": "2026-01-02", "emotion": "sad"},
    ]


# ── get_diary_session ─────────────────────────────────────────────────────────

def make_qna_item(sequence=1, question="How was your day?", answer="Good.",
                  asked_at=None, answered_at=None):
    from datetime import datetime, timezone
    item = MagicMock()
    item.sequence = sequence
    item.question = question
    item.answer = answer
    item.asked_at = asked_at or datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    item.answered_at = answered_at or datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    return item


def make_diary_entry(body="Today was nice.", summary="Nice day.", emotion="happy",
                     created_at=None):
    from datetime import datetime, timezone
    e = MagicMock()
    e.body = body
    e.summary = summary
    e.emotion = emotion
    e.created_at = created_at or datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return e


def make_qna_session(status="completed", diary_date="2026-01-01",
                     completed_at=None, items=None, diary_entry=None):
    from datetime import date, datetime, timezone
    s = MagicMock()
    s.status = status
    s.diary_date = date.fromisoformat(diary_date)
    s.completed_at = completed_at or (
        datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        if status == "completed" else None
    )
    s.items = items or []
    s.diary_entry = diary_entry
    return s


async def test_get_diary_session_invalid_date(session):
    from mcp_server.tools import get_diary_session
    result = await get_diary_session(session, 1, "not-a-date")
    assert result == {
        "status": "error",
        "code": "INVALID_DATE",
        "message": "date must be YYYY-MM-DD",
    }


async def test_get_diary_session_user_not_found(session):
    session.get = AsyncMock(return_value=None)
    from mcp_server.tools import get_diary_session
    result = await get_diary_session(session, 99, "2026-01-01")
    assert result["code"] == "USER_NOT_FOUND"


async def test_get_diary_session_no_session(session):
    session.get = AsyncMock(return_value=make_user())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_diary_session
    result = await get_diary_session(session, 1, "2026-01-01")
    assert result == {"status": "ok", "data": None}


async def test_get_diary_session_in_progress(session):
    item = make_qna_item(sequence=1, answer=None, answered_at=None)
    qna = make_qna_session(status="in_progress", items=[item], diary_entry=None)

    session.get = AsyncMock(return_value=make_user())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = qna
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_diary_session
    result = await get_diary_session(session, 1, "2026-01-01")
    assert result["status"] == "ok"
    assert result["data"]["status"] == "in_progress"
    assert result["data"]["diary"] is None
    assert result["data"]["completed_at"] is None


async def test_get_diary_session_completed(session):
    item1 = make_qna_item(sequence=1, question="Q1", answer="A1")
    item2 = make_qna_item(sequence=2, question="Q2", answer="A2")
    diary_entry = make_diary_entry(body="Full body.", summary="Summary.", emotion="happy")
    qna = make_qna_session(status="completed", items=[item2, item1], diary_entry=diary_entry)

    session.get = AsyncMock(return_value=make_user())
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = qna
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_diary_session
    result = await get_diary_session(session, 1, "2026-01-01")
    assert result["status"] == "ok"
    data = result["data"]
    assert data["status"] == "completed"
    assert data["diary"]["body"] == "Full body."
    assert data["diary"]["emotion"] == "happy"
    # items must be sorted by sequence
    assert data["qna_items"][0]["sequence"] == 1
    assert data["qna_items"][1]["sequence"] == 2


# ── get_user_schedules ────────────────────────────────────────────────────────

def make_schedule(id=1, period_start="2026-01-01", period_end="2026-01-07",
                  situation="Exam week", created_at=None):
    from datetime import date, datetime, timezone
    s = MagicMock()
    s.id = id
    s.period_start = date.fromisoformat(period_start)
    s.period_end = date.fromisoformat(period_end)
    s.situation = situation
    s.created_at = created_at or datetime(2026, 1, 1, tzinfo=timezone.utc)
    return s


async def test_get_user_schedules_user_not_found(session):
    session.get = AsyncMock(return_value=None)
    from mcp_server.tools import get_user_schedules
    result = await get_user_schedules(session, 99, None, None)
    assert result["code"] == "USER_NOT_FOUND"


async def test_get_user_schedules_invalid_date_from(session):
    from mcp_server.tools import get_user_schedules
    result = await get_user_schedules(session, 1, "bad", "2026-01-31")
    assert result["code"] == "INVALID_DATE"


async def test_get_user_schedules_invalid_date_to(session):
    from mcp_server.tools import get_user_schedules
    result = await get_user_schedules(session, 1, "2026-01-01", "oops")
    assert result["code"] == "INVALID_DATE"


async def test_get_user_schedules_no_filter(session):
    sched = make_schedule(id=1, period_start="2026-01-01", period_end="2026-01-07",
                          situation="Exam week")
    session.get = AsyncMock(return_value=make_user())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sched]
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_user_schedules
    result = await get_user_schedules(session, 1, None, None)
    assert result["status"] == "ok"
    assert result["data"][0]["situation"] == "Exam week"
    assert result["data"][0]["period_start"] == "2026-01-01"
    assert result["data"][0]["period_end"] == "2026-01-07"


async def test_get_user_schedules_with_date_range(session):
    session.get = AsyncMock(return_value=make_user())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    from mcp_server.tools import get_user_schedules
    result = await get_user_schedules(session, 1, "2026-02-01", "2026-02-28")
    assert result == {"status": "ok", "data": []}
