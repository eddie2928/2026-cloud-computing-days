from datetime import date

import pytest
from sqlalchemy import delete, select

from app.models import DiaryEntry, Pet
from app.routers.pet import XP_PER_DIARY


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _answer_n(client, session_id, start_seq, n):
    """Submit n answers starting from start_seq. Returns last response data."""
    seq = start_seq
    data = {}
    for i in range(n):
        resp = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"답변 {i+1}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        if data.get("sequence"):
            seq = data["sequence"]
    return data


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
async def test_qna_5_does_not_auto_finalize(client, bedrock_mock):
    """5th answer does NOT auto-complete — returns min_reached=True and next_question."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-02"})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]

    data = await _answer_n(client, session_id, body["sequence"], 5)
    assert data["completed"] is False
    assert data["min_reached"] is True
    assert data["next_question"]


@pytest.mark.asyncio
async def test_qna_finalize_after_5(client, bedrock_mock):
    """5 answers + POST /qna/finalize → diary created, session completed."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-12"})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]

    await _answer_n(client, session_id, body["sequence"], 5)

    resp = await client.post("/api/qna/finalize", json={"session_id": session_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diary"]


@pytest.mark.asyncio
async def test_qna_finalize_before_5_fails(client, bedrock_mock):
    """Finalize with fewer than 5 answers returns 400."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-13"})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]

    await _answer_n(client, session_id, body["sequence"], 4)

    resp = await client.post("/api/qna/finalize", json={"session_id": session_id})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_qna_finalize_idempotent(client, bedrock_mock):
    """Calling finalize twice returns the same diary."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-14"})
    body = start.json()
    session_id = body["session_id"]

    await _answer_n(client, session_id, body["sequence"], 5)

    resp1 = await client.post("/api/qna/finalize", json={"session_id": session_id})
    assert resp1.status_code == 200
    resp2 = await client.post("/api/qna/finalize", json={"session_id": session_id})
    assert resp2.status_code == 200
    assert resp1.json()["diary"] == resp2.json()["diary"]


@pytest.mark.asyncio
async def test_qna_unlimited_questions(client, bedrock_mock):
    """Answering beyond 5 still returns next_question each time."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-15"})
    body = start.json()
    session_id = body["session_id"]
    seq = body["sequence"]

    for i in range(10):
        resp = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"답변 {i+1}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["next_question"]
        assert data["completed"] is False
        seq = data["sequence"]

    assert seq == 11


@pytest.mark.asyncio
async def test_qna_response_includes_suggestions(client, bedrock_mock):
    """start and answer responses include suggestions list."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-16"})
    assert start.status_code == 200
    data = start.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)

    resp = await client.post(
        "/api/qna/answer",
        json={"session_id": data["session_id"], "sequence": data["sequence"], "answer": "테스트 답변"},
    )
    assert resp.status_code == 200
    answer_data = resp.json()
    assert "suggestions" in answer_data
    assert isinstance(answer_data["suggestions"], list)


@pytest.mark.asyncio
async def test_completed_date_returns_409(client, bedrock_mock):
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-03"})
    session_id = start.json()["session_id"]

    await _answer_n(client, session_id, start.json()["sequence"], 5)
    await client.post("/api/qna/finalize", json={"session_id": session_id})

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


@pytest.mark.asyncio
async def test_start_returns_history_on_resume(client, bedrock_mock):
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-07"})
    assert start.status_code == 200
    data = start.json()
    session_id = data["session_id"]
    seq = data["sequence"]

    await client.post(
        "/api/qna/answer",
        json={"session_id": session_id, "sequence": seq, "answer": "첫 번째 답변"},
    )

    resume = await client.post("/api/qna/start", json={"diary_date": "2026-05-07"})
    assert resume.status_code == 200
    resume_data = resume.json()
    assert resume_data["sequence"] == 2
    assert len(resume_data["history"]) == 1
    assert resume_data["history"][0]["sequence"] == 1
    assert resume_data["history"][0]["answer"] == "첫 번째 답변"


@pytest.mark.asyncio
async def test_profile_passed_to_bedrock_when_set(client, bedrock_mock):
    await _login(client)
    await client.put(
        "/api/profile",
        json={"nickname": "테스트유저", "gender": "other", "age": 20, "interests": ["커리어"]},
    )

    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-06"})
    assert start.status_code == 200

    call_kwargs = bedrock_mock.generate_question.call_args
    user_profile_arg = call_kwargs.kwargs.get("user_profile") or (
        call_kwargs.args[3] if len(call_kwargs.args) > 3 else None
    )
    assert user_profile_arg is not None
    assert user_profile_arg.get("nickname") == "테스트유저"


@pytest.mark.asyncio
async def test_diary_summary_saved_after_completion(client, bedrock_mock, db_session):
    """DiaryEntry.summary is populated when finalize is called."""
    await _login(client)
    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-10"})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]

    await _answer_n(client, session_id, body["sequence"], 5)
    await client.post("/api/qna/finalize", json={"session_id": session_id})

    result = await db_session.execute(
        select(DiaryEntry).where(DiaryEntry.diary_date == date(2026, 5, 10))
    )
    entry = result.scalar_one_or_none()
    assert entry is not None
    assert entry.summary == "오늘 하루 요약."


@pytest.mark.asyncio
async def test_pet_xp_grows_after_diary_completion(client, bedrock_mock, db_session):
    """Pet xp increases by XP_PER_DIARY after finalizing a diary."""
    await _login(client)
    await db_session.execute(delete(Pet).where(Pet.user_id == 1))
    await db_session.commit()

    start = await client.post("/api/qna/start", json={"diary_date": "2026-05-11"})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]

    await _answer_n(client, session_id, body["sequence"], 5)
    await client.post("/api/qna/finalize", json={"session_id": session_id})

    resp = await client.get("/api/pet")
    assert resp.status_code == 200
    assert resp.json()["xp"] == XP_PER_DIARY
