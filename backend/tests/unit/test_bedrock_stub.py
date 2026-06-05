import pytest
from unittest.mock import patch

from app.claude_stub import ClaudeStubClient, _STUB_QUESTIONS


@pytest.mark.asyncio
async def test_generate_question_returns_five_distinct_questions():
    client = ClaudeStubClient()
    questions = []
    for seq in range(1, 6):
        q, schedules, suggestions, meta = await client.generate_question([], [], seq)
        questions.append(q)
        assert isinstance(suggestions, list)
        assert meta["model_id"] == "stub"
        if seq != 3:
            assert schedules == [], f"sequence {seq}는 일정 없어야 함"
    assert len(set(questions)) == 5, "5개 시퀀스 질문이 서로 달라야 한다"


@pytest.mark.asyncio
async def test_generate_question_seq3_returns_schedule_with_time():
    """sequence=3에서 시간 포함 샘플 일정 1건 반환 (B4)."""
    client = ClaudeStubClient()
    _, schedules, _, _ = await client.generate_question([], [], 3)
    assert len(schedules) >= 1, "sequence=3은 일정 1건 이상 반환"
    sched = schedules[0]
    assert "start_time" in sched, "start_time 필드 필수"
    assert "end_time" in sched, "end_time 필드 필수"
    assert sched["start_time"], "start_time이 비어있으면 안 됨"


@pytest.mark.asyncio
async def test_generate_question_wraps_at_sequence_6():
    client = ClaudeStubClient()
    q1, _, _, _ = await client.generate_question([], [], 1)
    q6, _, _, _ = await client.generate_question([], [], 6)
    assert q1 == q6, "sequence=6은 sequence=1과 동일한 질문이어야 한다"


@pytest.mark.asyncio
async def test_generate_diary_returns_nonempty_body_and_summary():
    client = ClaudeStubClient()
    seen_bodies = set()
    for n in range(5):
        # qna_items 길이를 0~4로 변화시켜 5가지 다른 결과를 유도
        items = [object()] * n
        body, summary, meta = await client.generate_diary(items)
        assert body, "diary body는 빈 문자열이면 안 된다"
        assert summary, "diary summary는 빈 문자열이면 안 된다"
        assert meta["model_id"] == "stub"
        seen_bodies.add(body)
    assert len(seen_bodies) == 5, "5가지 입력 패턴이 서로 다른 diary body를 반환해야 한다"


@pytest.mark.asyncio
async def test_no_network_calls(monkeypatch):
    """stub 경로에서 AsyncAnthropic.messages.create가 호출되지 않음을 검증한다."""
    called = []

    async def mock_create(*args, **kwargs):
        called.append(args)

    monkeypatch.setattr("anthropic.AsyncAnthropic.messages", mock_create, raising=False)

    client = ClaudeStubClient()
    await client.generate_question([], [], 1)
    await client.generate_diary([])

    assert called == [], "ClaudeStubClient는 실제 API를 호출해서는 안 된다"
