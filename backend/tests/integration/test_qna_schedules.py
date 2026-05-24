"""Integration tests for schedule flow: pending_schedules in response, no auto-insert."""
from datetime import date

import pytest
from sqlalchemy import select

from app.models import UserSchedule


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pending_schedules_in_response(client, bedrock_mock, db_session):
    """Bedrock returns schedules → no auto-insert, pending_schedules in start response."""
    await _login(client)
    bedrock_mock.generate_question.return_value = (
        "오늘 어떤 일이 있었나요?",
        [{"period_start": "2026-07-01", "period_end": "2026-07-07", "situation": "기말 시험"}],
        {"model_id": "test"},
    )

    start = await client.post("/api/qna/start", json={"diary_date": "2026-07-10"})
    assert start.status_code == 200

    # DB에 자동 삽입 없음
    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.situation == "기말 시험")
    )
    rows = result.scalars().all()
    assert len(rows) == 0, "Bedrock schedules must NOT be auto-inserted"

    # 응답에 pending_schedules 포함
    data = start.json()
    pending = data.get("pending_schedules", [])
    assert len(pending) == 1
    assert pending[0]["situation"] == "기말 시험"
    assert pending[0]["period_start"] == "2026-07-01"
    assert pending[0]["period_end"] == "2026-07-07"


@pytest.mark.asyncio
async def test_empty_schedules_no_pending(client, bedrock_mock, db_session):
    """Empty schedules from Bedrock → pending_schedules is empty list."""
    await _login(client)
    bedrock_mock.generate_question.return_value = (
        "오늘 어떤 일이 있었나요?",
        [],
        {"model_id": "test"},
    )

    start = await client.post("/api/qna/start", json={"diary_date": "2026-09-10"})
    assert start.status_code == 200

    data = start.json()
    assert data.get("pending_schedules", []) == []

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.period_start == date(2026, 9, 10))
    )
    rows = result.scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_relevant_schedules_passed(client, bedrock_mock, db_session):
    """Manually inserted schedules are passed with correct labels to generate_question."""
    await _login(client)

    # Manually insert a schedule for Oct 2026 (진행 중 on 2026-10-15)
    result = await db_session.execute(select(UserSchedule).limit(0))
    from sqlalchemy import text
    await db_session.execute(
        text(
            "INSERT INTO user_schedules (user_id, period_start, period_end, situation) "
            "SELECT u.id, '2026-10-01', '2026-10-31', '10월 프로젝트' "
            "FROM users u LIMIT 1"
        )
    )
    await db_session.commit()

    bedrock_mock.generate_question.return_value = ("다음 질문", [], {"model_id": "test"})
    await client.post("/api/qna/start", json={"diary_date": "2026-10-15"})

    call_kwargs = bedrock_mock.generate_question.call_args
    relevant_schedules_arg = call_kwargs.kwargs.get("relevant_schedules") or []
    assert any("10월 프로젝트" in s for s in relevant_schedules_arg)
    assert any("[진행중]" in s for s in relevant_schedules_arg)


@pytest.mark.asyncio
async def test_recently_ended_schedule_included(client, bedrock_mock, db_session):
    """Schedule ended within 7 days is included with [N일 전 종료] label."""
    await _login(client)

    from sqlalchemy import text
    # Insert schedule ending 3 days before diary date
    await db_session.execute(
        text(
            "INSERT INTO user_schedules (user_id, period_start, period_end, situation) "
            "SELECT u.id, '2026-11-01', '2026-11-12', '종료 일정' "
            "FROM users u LIMIT 1"
        )
    )
    await db_session.commit()

    bedrock_mock.generate_question.return_value = ("질문", [], {"model_id": "test"})
    await client.post("/api/qna/start", json={"diary_date": "2026-11-15"})

    call_kwargs = bedrock_mock.generate_question.call_args
    relevant_schedules_arg = call_kwargs.kwargs.get("relevant_schedules") or []
    assert any("종료 일정" in s for s in relevant_schedules_arg)
    assert any("전 종료" in s for s in relevant_schedules_arg)


@pytest.mark.asyncio
async def test_old_ended_schedule_excluded(client, bedrock_mock, db_session):
    """Schedule ended more than 7 days ago is excluded from relevant_schedules."""
    await _login(client)

    from sqlalchemy import text
    # Insert schedule ending 10 days before diary date
    await db_session.execute(
        text(
            "INSERT INTO user_schedules (user_id, period_start, period_end, situation) "
            "SELECT u.id, '2026-12-01', '2026-12-05', '오래된 일정' "
            "FROM users u LIMIT 1"
        )
    )
    await db_session.commit()

    bedrock_mock.generate_question.return_value = ("질문", [], {"model_id": "test"})
    await client.post("/api/qna/start", json={"diary_date": "2026-12-20"})

    call_kwargs = bedrock_mock.generate_question.call_args
    relevant_schedules_arg = call_kwargs.kwargs.get("relevant_schedules") or []
    assert not any("오래된 일정" in s for s in relevant_schedules_arg)
