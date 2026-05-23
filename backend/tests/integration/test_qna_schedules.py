"""Integration tests for schedule extraction + INSERT + duplicate skip (todo #10.4)."""
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import UserSchedule


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _full_qna(client, bedrock_mock, diary_date: str):
    start = await client.post("/api/qna/start", json={"diary_date": diary_date})
    assert start.status_code == 200
    data = start.json()
    session_id = data["session_id"]
    seq = data["sequence"]
    for i in range(1, 6):
        resp = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"답변 {i}"},
        )
        assert resp.status_code == 200
        resp_data = resp.json()
        if not resp_data.get("completed"):
            seq = resp_data["sequence"]


@pytest.mark.asyncio
async def test_schedules_inserted_from_bedrock(client, bedrock_mock, db_session):
    """Schedules extracted by Bedrock are inserted into user_schedules."""
    await _login(client)
    bedrock_mock.generate_question.return_value = (
        "오늘 어떤 일이 있었나요?",
        [{"period_start": "2026-07-01", "period_end": "2026-07-07", "situation": "기말 시험"}],
        {"model_id": "test"},
    )

    start = await client.post("/api/qna/start", json={"diary_date": "2026-07-10"})
    assert start.status_code == 200

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.situation == "기말 시험")
    )
    rows = result.scalars().all()
    assert len(rows) >= 1
    assert rows[0].period_start == date(2026, 7, 1)
    assert rows[0].period_end == date(2026, 7, 7)


@pytest.mark.asyncio
async def test_duplicate_schedule_skipped(client, bedrock_mock, db_session):
    """Duplicate (user_id, period_start, period_end, situation) is not inserted twice."""
    await _login(client)
    bedrock_mock.generate_question.return_value = (
        "오늘 어떤 일이 있었나요?",
        [{"period_start": "2026-08-01", "period_end": "2026-08-05", "situation": "중복 테스트"}],
        {"model_id": "test"},
    )

    await client.post("/api/qna/start", json={"diary_date": "2026-08-10"})
    await client.post("/api/qna/start", json={"diary_date": "2026-08-11"})

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.situation == "중복 테스트")
    )
    rows = result.scalars().all()
    assert len(rows) == 1, "Duplicate schedule should not be inserted twice"


@pytest.mark.asyncio
async def test_empty_schedules_no_insert(client, bedrock_mock, db_session):
    """Empty schedules list from Bedrock results in no UserSchedule INSERT."""
    await _login(client)
    bedrock_mock.generate_question.return_value = (
        "오늘 어떤 일이 있었나요?",
        [],
        {"model_id": "test"},
    )

    start = await client.post("/api/qna/start", json={"diary_date": "2026-09-10"})
    assert start.status_code == 200

    result = await db_session.execute(
        select(UserSchedule).where(UserSchedule.period_start == date(2026, 9, 10))
    )
    rows = result.scalars().all()
    assert rows == []
