"""Unit tests for bedrock parsing (todos #8.4, #13.2)."""
import re
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bedrock import BedrockClient, _build_rag_block


def _make_client():
    with patch("app.bedrock.boto3.client"):
        return BedrockClient(region="us-east-1", model_id="test-model")


def _mock_invoke(text: str):
    meta = {"model_id": "test-model", "input_tokens": 10, "output_tokens": 20, "latency_ms": 100}
    return text, meta


def _make_item(seq: int, question: str = "질문", answer: str = "답변"):
    item = MagicMock()
    item.sequence = seq
    item.question = question
    item.answer = answer
    return item


@pytest.mark.asyncio
async def test_generate_diary_normal_parse():
    """<diary> and <summary> tags parsed correctly."""
    client = _make_client()
    raw = "<diary>오늘은 좋은 날이었다.</diary>\n<summary>좋은 하루 요약.</summary>"
    items = [_make_item(1), _make_item(2)]

    with patch("app.bedrock._invoke_claude", return_value=(raw, {})):
        body, summary, meta = await client.generate_diary(items)

    assert body == "오늘은 좋은 날이었다."
    assert summary == "좋은 하루 요약."


@pytest.mark.asyncio
async def test_generate_diary_no_tags_fallback():
    """When tags are absent, entire text becomes body and summary is empty."""
    client = _make_client()
    raw = "태그 없는 일기 본문입니다."
    items = [_make_item(1)]

    with patch("app.bedrock._invoke_claude", return_value=(raw, {})):
        body, summary, meta = await client.generate_diary(items)

    assert body == raw
    assert summary == ""


@pytest.mark.asyncio
async def test_generate_diary_markdown_mixed():
    """Markdown noise outside tags is ignored; tags still parsed."""
    client = _make_client()
    raw = (
        "## 결과\n"
        "<diary>마크다운 혼합 일기 내용입니다.</diary>\n"
        "<summary>마크다운 혼합 요약.</summary>\n"
        "---"
    )
    items = [_make_item(1)]

    with patch("app.bedrock._invoke_claude", return_value=(raw, {})):
        body, summary, meta = await client.generate_diary(items)

    assert body == "마크다운 혼합 일기 내용입니다."
    assert summary == "마크다운 혼합 요약."


def test_build_rag_block_with_summaries():
    """rag_summaries list serialized as [YYYY-MM-DD] summary lines."""
    summaries = [
        (date(2026, 5, 20), "첫 번째 요약"),
        (date(2026, 5, 19), "두 번째 요약"),
    ]
    result = _build_rag_block(summaries)
    assert "[2026-05-20] 첫 번째 요약" in result
    assert "[2026-05-19] 두 번째 요약" in result


def test_build_rag_block_empty():
    """Empty list returns fallback string."""
    result = _build_rag_block([])
    assert result == "이전 일기 없음"
