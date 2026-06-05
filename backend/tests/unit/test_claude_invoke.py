"""Unit test for _invoke_claude: verifies (text, meta) extraction without network."""
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("CLAUDE_MODEL", "claude-sonnet-4-6")

from app.claude import _invoke_claude


def _make_response(text: str, input_tokens: int, output_tokens: int):
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    resp = MagicMock()
    resp.content = [content_block]
    resp.usage = usage
    return resp


@pytest.mark.asyncio
async def test_invoke_claude_returns_correct_text_and_meta():
    """_invoke_claude extracts text and builds meta dict from AsyncAnthropic response."""
    fake_resp = _make_response("오늘 어떤 일이 있었나요?", input_tokens=10, output_tokens=5)

    mock_messages = AsyncMock()
    mock_messages.create = AsyncMock(return_value=fake_resp)

    mock_client = MagicMock()
    mock_client.messages = mock_messages

    with patch("app.claude.AsyncAnthropic", return_value=mock_client):
        text, meta = await _invoke_claude("claude-sonnet-4-6", "test prompt", max_tokens=1024)

    assert text == "오늘 어떤 일이 있었나요?"
    assert meta["input_tokens"] == 10
    assert meta["output_tokens"] == 5
    assert meta["model_id"] == "claude-sonnet-4-6"
    assert meta["prompt"] == "test prompt"
    assert meta["raw_response"] == text
    assert isinstance(meta["latency_ms"], int)


@pytest.mark.asyncio
async def test_invoke_claude_no_text_block_returns_empty():
    """When response has no text-type block, text is empty string."""
    content_block = MagicMock()
    content_block.type = "thinking"
    content_block.text = "..."

    usage = MagicMock()
    usage.input_tokens = 5
    usage.output_tokens = 2

    fake_resp = MagicMock()
    fake_resp.content = [content_block]
    fake_resp.usage = usage

    mock_messages = AsyncMock()
    mock_messages.create = AsyncMock(return_value=fake_resp)
    mock_client = MagicMock()
    mock_client.messages = mock_messages

    with patch("app.claude.AsyncAnthropic", return_value=mock_client):
        text, meta = await _invoke_claude("claude-sonnet-4-6", "prompt", max_tokens=512)

    assert text == ""


@pytest.mark.asyncio
async def test_invoke_claude_messages_create_called_with_correct_args():
    """messages.create is called with the expected model, max_tokens, and messages."""
    fake_resp = _make_response("Q", input_tokens=1, output_tokens=1)

    mock_messages = AsyncMock()
    mock_messages.create = AsyncMock(return_value=fake_resp)
    mock_client = MagicMock()
    mock_client.messages = mock_messages

    with patch("app.claude.AsyncAnthropic", return_value=mock_client):
        await _invoke_claude("claude-sonnet-4-6", "my prompt", max_tokens=2048)

    mock_messages.create.assert_called_once_with(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": "my prompt"}],
    )
