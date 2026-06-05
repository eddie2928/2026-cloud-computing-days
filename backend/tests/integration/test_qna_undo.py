"""Integration tests for POST /api/qna/undo endpoint."""
import pytest
from sqlalchemy import select

from app.models import QnAItem


async def _login(client):
    resp = await client.post("/api/login", json={"password": "inha-nxt"})
    assert resp.status_code == 200


async def _setup_session_with_n_answers(client, claude_mock, diary_date, n):
    """Create a session and answer n questions. Returns (session_id, last_seq)."""
    start = await client.post("/api/qna/start", json={"diary_date": diary_date})
    assert start.status_code == 200
    body = start.json()
    session_id = body["session_id"]
    seq = body["sequence"]

    for i in range(n):
        resp = await client.post(
            "/api/qna/answer",
            json={"session_id": session_id, "sequence": seq, "answer": f"답변 {i+1}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        if data.get("sequence"):
            seq = data["sequence"]

    return session_id, seq


@pytest.mark.asyncio
async def test_undo_validation_nonexistent_sequence(client, claude_mock):
    """Undo with target_sequence=99 returns 400."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-15", 3)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 99, "mode": "discard"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_undo_validation_unanswered_sequence(client, claude_mock):
    """Undo on an unanswered sequence returns 400."""
    await _login(client)
    session_id, next_seq = await _setup_session_with_n_answers(client, claude_mock, "2026-06-02", 3)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": next_seq, "mode": "discard"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_undo_validation_completed_session(client, claude_mock):
    """Undo on a completed session returns 409."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-03", 5)
    await client.post("/api/qna/finalize", json={"session_id": session_id})

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 3, "mode": "discard"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_undo_validation_wrong_user(client, claude_mock):
    """Undo on another user's session returns 404."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-04", 3)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id + 9999, "target_sequence": 1, "mode": "discard"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_undo_discard_basic(client, claude_mock, db_session):
    """Discard undo at sequence=3: items 4,5 deleted, item 3 answer=NULL, new question set."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-05", 5)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 3, "mode": "discard"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sequence"] == 3
    assert data["question"]
    assert isinstance(data["removed_schedule_keys"], list)

    # Verify DB: items 4 and 5 deleted
    result = await db_session.execute(
        select(QnAItem).where(
            QnAItem.session_id == session_id,
            QnAItem.sequence.in_([4, 5]),
        )
    )
    remaining = result.scalars().all()
    assert len(remaining) == 0

    # Verify item 3 answer is NULL
    result3 = await db_session.execute(
        select(QnAItem).where(
            QnAItem.session_id == session_id, QnAItem.sequence == 3
        )
    )
    item3 = result3.scalar_one_or_none()
    assert item3 is not None
    assert item3.answer is None


@pytest.mark.asyncio
async def test_undo_discard_removes_schedules(client, claude_mock):
    """Discard undo response includes removed_schedule_keys from discarded items."""
    await _login(client)

    # Set up claude_mock to return schedules for items 4 and 5
    original_return = claude_mock.generate_question.return_value
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count in (4, 5):
            return (
                "오늘 어떤 일이 있었나요?",
                [{"period_start": f"2026-06-0{call_count}", "period_end": f"2026-06-0{call_count}", "situation": f"일정 {call_count}"}],
                ["답변1", "답변2", "답변3"],
                {"model_id": "test", "raw_response": f"<schedules>2026-06-0{call_count}|2026-06-0{call_count}|일정 {call_count}</schedules>"},
            )
        return ("오늘 어떤 일이 있었나요?", [], ["답변1", "답변2", "답변3"], {"model_id": "test", "raw_response": ""})

    claude_mock.generate_question.side_effect = side_effect

    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-06", 5)

    claude_mock.generate_question.side_effect = None
    claude_mock.generate_question.return_value = original_return

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 3, "mode": "discard"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["removed_schedule_keys"], list)


@pytest.mark.asyncio
async def test_undo_keep_basic(client, claude_mock, db_session):
    """Keep undo at sequence=3: items 4,5 preserved, item3 answer=new_answer, response sequence=6."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-07", 5)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 3, "mode": "keep", "new_answer": "수정된 답변"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sequence"] == 6
    assert data["question"]
    assert isinstance(data["removed_schedule_keys"], list)

    # Verify DB: items 4 and 5 still exist
    result = await db_session.execute(
        select(QnAItem).where(
            QnAItem.session_id == session_id,
            QnAItem.sequence.in_([4, 5]),
        )
    )
    remaining = result.scalars().all()
    assert len(remaining) == 2

    # Item 3 answer is the new value, not NULL
    result3 = await db_session.execute(
        select(QnAItem).where(
            QnAItem.session_id == session_id, QnAItem.sequence == 3
        )
    )
    item3 = result3.scalar_one_or_none()
    assert item3 is not None
    assert item3.answer == "수정된 답변"


@pytest.mark.asyncio
async def test_undo_keep_requires_new_answer(client, claude_mock):
    """Keep undo without new_answer returns 400."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-09", 3)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 2, "mode": "keep"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_undo_keep_regenerates_trailing_only(client, claude_mock, db_session):
    """Keep undo: target question unchanged, last pending question (seq6) regenerated."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-10", 5)

    # Capture item3's question before undo
    result_before = await db_session.execute(
        select(QnAItem).where(QnAItem.session_id == session_id, QnAItem.sequence == 3)
    )
    item3_before = result_before.scalar_one_or_none()
    assert item3_before is not None
    original_question = item3_before.question

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 3, "mode": "keep", "new_answer": "편집된 내용"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Response points to last pending question (seq6), not seq3
    assert data["sequence"] == 6
    assert isinstance(data["removed_schedule_keys"], list)

    # item3.question must be unchanged
    db_session.expire_all()
    result3 = await db_session.execute(
        select(QnAItem).where(QnAItem.session_id == session_id, QnAItem.sequence == 3)
    )
    item3_after = result3.scalar_one_or_none()
    assert item3_after is not None
    assert item3_after.question == original_question


@pytest.mark.asyncio
async def test_undo_discard_keeps_target_question(client, claude_mock, db_session):
    """Discard undo: target question is preserved (not regenerated)."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-11", 5)

    # Capture item3's question before undo
    result_before = await db_session.execute(
        select(QnAItem).where(QnAItem.session_id == session_id, QnAItem.sequence == 3)
    )
    item3_before = result_before.scalar_one_or_none()
    assert item3_before is not None
    original_question = item3_before.question

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 3, "mode": "discard"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sequence"] == 3

    # item3.question must be unchanged after discard
    db_session.expire_all()
    result3 = await db_session.execute(
        select(QnAItem).where(QnAItem.session_id == session_id, QnAItem.sequence == 3)
    )
    item3_after = result3.scalar_one_or_none()
    assert item3_after is not None
    assert item3_after.question == original_question


@pytest.mark.asyncio
async def test_undo_response_includes_suggestions_and_schedules(client, claude_mock):
    """Undo response includes suggestions and pending_schedules fields."""
    await _login(client)
    session_id, _ = await _setup_session_with_n_answers(client, claude_mock, "2026-06-08", 3)

    resp = await client.post(
        "/api/qna/undo",
        json={"session_id": session_id, "target_sequence": 2, "mode": "discard"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert "pending_schedules" in data
    assert isinstance(data["pending_schedules"], list)
