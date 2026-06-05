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


@pytest.mark.asyncio
async def test_get_diary_after_completion(client, claude_mock):
    await _login(client)
    await _complete_qna(client, claude_mock, "2026-06-01")

    resp = await client.get("/api/diary/2026-06-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["body"]
    assert data["date"] == "2026-06-01"
    assert data["emotion"] == "neutral"


@pytest.mark.asyncio
async def test_get_diary_not_found(client, claude_mock):
    await _login(client)
    resp = await client.get("/api/diary/2099-12-31")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_calendar_includes_completed_date(client, claude_mock):
    await _login(client)
    await _complete_qna(client, claude_mock, "2026-07-15")

    resp = await client.get("/api/calendar", params={"month": "2026-07"})
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    dates = [e["date"] for e in entries]
    assert "2026-07-15" in dates
    entry = next(e for e in entries if e["date"] == "2026-07-15")
    assert entry["emotion"] == "neutral"


@pytest.mark.asyncio
async def test_calendar_excludes_other_month(client, claude_mock):
    await _login(client)
    await _complete_qna(client, claude_mock, "2026-08-20")

    resp = await client.get("/api/calendar", params={"month": "2026-07"})
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    dates = [e["date"] for e in entries]
    assert "2026-08-20" not in dates


@pytest.mark.asyncio
async def test_calendar_entry_has_written_date(client, claude_mock):
    """written_date 필드가 CalendarEntry 응답에 존재하는지 확인"""
    await _login(client)
    await _complete_qna(client, claude_mock, "2026-09-10")

    resp = await client.get("/api/calendar", params={"month": "2026-09"})
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    entry = next(e for e in entries if e["date"] == "2026-09-10")
    assert "written_date" in entry
    assert entry["written_date"] is not None


@pytest.mark.asyncio
async def test_calendar_written_date_same_day(client, db_session, claude_mock):
    """created_at이 diary_date와 같은 KST 날짜이면 written_date == date"""
    await _login(client)
    await _complete_qna(client, claude_mock, "2026-10-05")

    # 2026-10-05T05:00:00 UTC = 2026-10-05T14:00:00 KST → 같은 날
    same_day_utc = datetime(2026, 10, 5, 5, 0, 0, tzinfo=timezone.utc)
    from sqlalchemy import text
    await db_session.execute(
        text("UPDATE diary_entries SET created_at = :ts WHERE diary_date = '2026-10-05'"),
        {"ts": same_day_utc},
    )
    await db_session.commit()

    resp = await client.get("/api/calendar", params={"month": "2026-10"})
    entries = resp.json()["entries"]
    entry = next(e for e in entries if e["date"] == "2026-10-05")
    assert entry["written_date"] == "2026-10-05"


@pytest.mark.asyncio
async def test_calendar_kst_midnight_boundary(client, db_session, claude_mock):
    """UTC 15:30 = KST 다음날 00:30: written_date가 diary_date + 1일로 나와야 함"""
    await _login(client)
    await _complete_qna(client, claude_mock, "2026-11-20")

    # 2026-11-20T15:30:00 UTC = 2026-11-21T00:30:00 KST → 다음 날
    next_day_utc = datetime(2026, 11, 20, 15, 30, 0, tzinfo=timezone.utc)
    from sqlalchemy import text
    await db_session.execute(
        text("UPDATE diary_entries SET created_at = :ts WHERE diary_date = '2026-11-20'"),
        {"ts": next_day_utc},
    )
    await db_session.commit()

    resp = await client.get("/api/calendar", params={"month": "2026-11"})
    entries = resp.json()["entries"]
    entry = next(e for e in entries if e["date"] == "2026-11-20")
    assert entry["written_date"] == "2026-11-21"
    assert entry["written_date"] != entry["date"]
