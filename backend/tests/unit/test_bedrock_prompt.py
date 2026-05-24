import os
from datetime import date, datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")


def _make_item(seq: int, question: str, answer: str | None = None, days_ago: int = 0) -> MagicMock:
    item = MagicMock()
    item.sequence = seq
    item.question = question
    item.answer = answer
    item.asked_at = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return item


def test_empty_rag_contains_no_previous():
    from app.bedrock import _build_rag_block

    result = _build_rag_block([])
    assert "이전 일기 없음" in result


def test_rag_summaries_sorted_newest_first():
    from app.bedrock import _build_rag_block

    summaries = [
        (date(2026, 5, 25), "최근 요약"),
        (date(2026, 5, 22), "중간 요약"),
        (date(2026, 5, 20), "오래된 요약"),
    ]
    result = _build_rag_block(summaries)
    pos_recent = result.index("최근 요약")
    pos_mid = result.index("중간 요약")
    pos_old = result.index("오래된 요약")
    assert pos_recent < pos_mid < pos_old, "Summaries should appear newest first"


def test_session_partial_includes_only_answered():
    from app.bedrock import _build_session_block

    items = [
        _make_item(1, "Q1", "A1"),
        _make_item(2, "Q2", "A2"),
        _make_item(3, "Q3", None),
    ]
    result = _build_session_block(items)
    assert "A1" in result
    assert "A2" in result
    assert "Q3" not in result or "A3" not in result


def test_profile_block_with_profile():
    from app.bedrock import _build_profile_block

    profile = {"nickname": "수진", "occupation": "개발자", "interests": ["커리어", "건강"], "hobbies": ["독서"]}
    result = _build_profile_block(profile)
    assert "수진" in result
    assert "개발자" in result
    assert "커리어" in result
    assert "독서" in result


def test_profile_block_without_profile():
    from app.bedrock import _build_profile_block

    result = _build_profile_block(None)
    assert result == ""


def test_relevant_schedules_substituted():
    from app.bedrock import _load_prompt

    result = _load_prompt(
        "question",
        user_profile="",
        rag_summaries="",
        relevant_schedules="[진행중] 테스트 일정 (2026-05-01~2026-05-31)",
        session_so_far="",
        next_sequence="1",
    )
    assert "진행중" in result
    assert "테스트 일정" in result
    assert "active_schedules" not in result


def test_empty_relevant_schedules_no_placeholder_left():
    from app.bedrock import _load_prompt

    result = _load_prompt(
        "question",
        user_profile="",
        rag_summaries="",
        relevant_schedules="",
        session_so_far="",
        next_sequence="1",
    )
    assert "{{relevant_schedules}}" not in result
    assert "{{active_schedules}}" not in result
