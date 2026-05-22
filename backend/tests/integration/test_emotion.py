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
        if not d.get("completed"):
            seq = d["sequence"]


@pytest.mark.asyncio
async def test_patch_emotion_success(client, bedrock_mock):
    await _login(client)
    await _complete_qna(client, "2026-09-01")

    resp = await client.patch("/api/diary/2026-09-01/emotion", json={"emotion": "happy"})
    assert resp.status_code == 200
    assert resp.json()["emotion"] == "happy"

    get_resp = await client.get("/api/diary/2026-09-01")
    assert get_resp.json()["emotion"] == "happy"


@pytest.mark.asyncio
async def test_patch_emotion_invalid_value(client, bedrock_mock):
    await _login(client)
    await _complete_qna(client, "2026-09-02")

    resp = await client.patch("/api/diary/2026-09-02/emotion", json={"emotion": "excited"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_emotion_diary_not_found(client, bedrock_mock):
    await _login(client)
    resp = await client.patch("/api/diary/2099-01-01/emotion", json={"emotion": "sad"})
    assert resp.status_code == 404
