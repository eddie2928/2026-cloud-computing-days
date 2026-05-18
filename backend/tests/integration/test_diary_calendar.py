import pytest


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _complete_qna(client, bedrock_mock, diary_date: str):
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
async def test_get_diary_after_completion(client, bedrock_mock):
    await _login(client)
    await _complete_qna(client, bedrock_mock, "2026-06-01")

    resp = await client.get("/api/diary/2026-06-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["body"]
    assert data["date"] == "2026-06-01"


@pytest.mark.asyncio
async def test_get_diary_not_found(client, bedrock_mock):
    await _login(client)
    resp = await client.get("/api/diary/2099-12-31")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_calendar_includes_completed_date(client, bedrock_mock):
    await _login(client)
    await _complete_qna(client, bedrock_mock, "2026-07-15")

    resp = await client.get("/api/calendar", params={"month": "2026-07"})
    assert resp.status_code == 200
    dates = resp.json()["dates"]
    assert "2026-07-15" in dates


@pytest.mark.asyncio
async def test_calendar_excludes_other_month(client, bedrock_mock):
    await _login(client)
    await _complete_qna(client, bedrock_mock, "2026-08-20")

    resp = await client.get("/api/calendar", params={"month": "2026-07"})
    assert resp.status_code == 200
    dates = resp.json()["dates"]
    assert "2026-08-20" not in dates
