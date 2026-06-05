"""
@reusable
@scope project-local
@description KST timezone 변환 로직 검증 패턴 — UTC created_at을 KST로 변환한 written_date 필드 검증
@usage diary_entries 테이블 및 API 경로(/api/calendar)가 동일해야 함. created_at 직접 조작은 db_session fixture 필요.
@origin proj_days / task: CalendarEntry written_date 필드 추가 (2026-05-28)
@created 2026-05-28T00:00:00+09:00
"""
import pytest
from datetime import datetime, timezone


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _complete_qna(client, claude_mock, diary_date: str):
    start = await client.post("/api/qna/start", json={"diary_date": diary_date})
    data = start.json()
    session_id = data["session_id"]
    seq = data["sequence"]

    for i in range(1, 6):
        resp = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"답변{i}"},
        )
        d = resp.json()
        if not d.get("completed"):
            seq = d["sequence"]
    await client.post("/api/qna/finalize", json={"session_id": session_id})


@pytest.mark.asyncio
async def test_calendar_written_date_same_day(client, db_session, claude_mock):
    """
    @reusable
    created_at이 diary_date와 같은 KST 날짜이면 written_date == date.
    패턴: db_session.commit()으로 created_at을 직접 조작한 후 API 응답 검증.
    향후 타임스탬프 기반 로직 테스트에 참고 가능.
    """
    await _login(client)
    await _complete_qna(client, claude_mock, "2025-10-05")

    # 2025-10-05T05:00:00 UTC = 2025-10-05T14:00:00 KST → 같은 날
    same_day_utc = datetime(2025, 10, 5, 5, 0, 0, tzinfo=timezone.utc)
    from sqlalchemy import text
    await db_session.execute(
        text("UPDATE diary_entries SET created_at = :ts WHERE diary_date = '2025-10-05'"),
        {"ts": same_day_utc},
    )
    await db_session.commit()

    resp = await client.get("/api/calendar", params={"month": "2025-10"})
    entries = resp.json()["entries"]
    entry = next(e for e in entries if e["date"] == "2025-10-05")
    assert entry["written_date"] == "2025-10-05"


@pytest.mark.asyncio
async def test_calendar_kst_midnight_boundary(client, db_session, claude_mock):
    """
    @reusable
    UTC 15:30 = KST 다음날 00:30: written_date가 diary_date + 1일로 나와야 함.
    패턴: KST 자정 경계(UTC+9 = 15:00 UTC) 검증. timezone 변환 로직 변경 시 회귀 방지에 활용 가능.
    """
    await _login(client)
    await _complete_qna(client, claude_mock, "2025-11-20")

    # 2025-11-20T15:30:00 UTC = 2025-11-21T00:30:00 KST → 다음 날
    next_day_utc = datetime(2025, 11, 20, 15, 30, 0, tzinfo=timezone.utc)
    from sqlalchemy import text
    await db_session.execute(
        text("UPDATE diary_entries SET created_at = :ts WHERE diary_date = '2025-11-20'"),
        {"ts": next_day_utc},
    )
    await db_session.commit()

    resp = await client.get("/api/calendar", params={"month": "2025-11"})
    entries = resp.json()["entries"]
    entry = next(e for e in entries if e["date"] == "2025-11-20")
    assert entry["written_date"] == "2025-11-21"
    assert entry["written_date"] != entry["date"]
