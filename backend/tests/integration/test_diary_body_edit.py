import pytest


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _complete_qna(client, diary_date: str):
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
        if d.get("sequence"):
            seq = d["sequence"]
    await client.post("/api/qna/finalize", json={"session_id": session_id})


@pytest.mark.asyncio
async def test_patch_body_success(client, claude_mock):
    await _login(client)
    await _complete_qna(client, "2026-10-01")

    resp = await client.patch("/api/diary/2026-10-01/body", json={"body": "수정된 일기 내용입니다."})
    assert resp.status_code == 200
    assert resp.json()["body"] == "수정된 일기 내용입니다."

    get_resp = await client.get("/api/diary/2026-10-01")
    assert get_resp.json()["body"] == "수정된 일기 내용입니다."


@pytest.mark.asyncio
async def test_patch_body_404(client, claude_mock):
    await _login(client)
    resp = await client.patch("/api/diary/2099-12-31/body", json={"body": "없는 날짜"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_body_validation(client, claude_mock):
    await _login(client)
    resp = await client.patch("/api/diary/2026-10-01/body", json={"body": ""})
    assert resp.status_code == 422
