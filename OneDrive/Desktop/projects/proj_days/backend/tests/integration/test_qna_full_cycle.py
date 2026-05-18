import pytest


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_start_returns_first_question(client, bedrock_mock):
    await _login(client)
    resp = await client.post("/api/qna/start", json={"diary_date": "2026-05-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sequence"] == 1
    assert data["question"]
    assert data["session_id"]


@pytest.mark.asyncio
async def test_full_five_answer_cycle_completes(client, bedrock_mock):
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-02"})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]
    seq = body["sequence"]

    for i in range(1, 6):
        resp = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"답변 {i}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        if i < 5:
            assert not data["completed"]
            seq = data["sequence"]
        else:
            assert data["completed"]
            assert data["diary"]


@pytest.mark.asyncio
async def test_completed_date_returns_409(client, bedrock_mock):
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-03"})
    session_id = start.json()["session_id"]
    seq = start.json()["sequence"]

    for i in range(1, 6):
        r = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"a{i}"},
        )
        if not r.json().get("completed"):
            seq = r.json()["sequence"]

    resp = await client.post("/api/qna/start", json={"diary_date": "2026-05-03"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_in_progress_session_can_resume(client, bedrock_mock):
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-04"})
    assert start.status_code == 200
    data = start.json()
    session_id = data["session_id"]
    seq = data["sequence"]

    await client.post(
        "/api/qna/answer",
        json={"session_id": session_id, "sequence": seq, "answer": "첫 번째 답변"},
    )

    resume = await client.post("/api/qna/start", json={"diary_date": "2026-05-04"})
    assert resume.status_code == 200
    resume_data = resume.json()
    assert resume_data["sequence"] == 2


@pytest.mark.asyncio
async def test_wrong_sequence_returns_400(client, bedrock_mock):
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-05"})
    session_id = start.json()["session_id"]

    resp = await client.post(
        "/api/qna/answer",
        json={"session_id": session_id, "sequence": 99, "answer": "잘못된 순서"},
    )
    assert resp.status_code == 400
