"""Unit tests for bedrock parsing (todos #8.4, #13.2, #10.3)."""
import re
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bedrock import BedrockClient, _build_rag_block, _parse_schedules


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


@pytest.mark.skip(reason="BedrockClient는 현재 BedrockStubClient로 re-export됨 — _invoke_claude/boto3 mock 불필요 (수동 마이그레이션 기간)")
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


@pytest.mark.skip(reason="BedrockClient는 현재 BedrockStubClient로 re-export됨 — _invoke_claude/boto3 mock 불필요 (수동 마이그레이션 기간)")
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


@pytest.mark.skip(reason="BedrockClient는 현재 BedrockStubClient로 re-export됨 — _invoke_claude/boto3 mock 불필요 (수동 마이그레이션 기간)")
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


def test_parse_schedules_normal():
    """Normal schedule lines parsed correctly."""
    raw = "<question>질문</question>\n<schedules>\n2026-06-01|2026-06-07|기말 시험\n2026-06-10|2026-06-12|여행\n</schedules>"
    result = _parse_schedules(raw)
    assert len(result) == 2
    assert result[0] == {"period_start": "2026-06-01", "period_end": "2026-06-07", "situation": "기말 시험"}
    assert result[1] == {"period_start": "2026-06-10", "period_end": "2026-06-12", "situation": "여행"}


def test_parse_schedules_empty_body():
    """Empty schedules block returns empty list."""
    raw = "<question>질문</question>\n<schedules></schedules>"
    result = _parse_schedules(raw)
    assert result == []


def test_parse_schedules_malformed_line_skipped():
    """Malformed lines are skipped; valid lines still parsed."""
    raw = "<schedules>\n잘못된줄\n2026-06-01|2026-06-07|정상 일정\n</schedules>"
    result = _parse_schedules(raw)
    assert len(result) == 1
    assert result[0]["situation"] == "정상 일정"
