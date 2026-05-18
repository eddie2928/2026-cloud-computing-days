import os
from datetime import datetime, timezone, timedelta
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


def test_rag_items_sorted_newest_first():
    from app.bedrock import _build_rag_block

    items = [
        _make_item(1, "Q1", "A1", days_ago=5),
        _make_item(2, "Q2", "A2", days_ago=1),
        _make_item(3, "Q3", "A3", days_ago=3),
    ]
    result = _build_rag_block(items)
    lines = [l for l in result.split("\n") if l.strip()]
    texts = [l for l in lines]
    a2_pos = next(i for i, t in enumerate(texts) if "A2" in t)
    a3_pos = next(i for i, t in enumerate(texts) if "A3" in t)
    a1_pos = next(i for i, t in enumerate(texts) if "A1" in t)
    assert a2_pos < a3_pos < a1_pos, "Items should be sorted newest first"


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
