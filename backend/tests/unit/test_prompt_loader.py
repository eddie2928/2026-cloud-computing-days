"""Unit tests for _load_prompt helper (todo #9.3)."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")


def test_normal_substitution(tmp_path):
    """Variables are substituted correctly."""
    prompt_file = tmp_path / "test_prompt.md"
    prompt_file.write_text("안녕 {{name}}, 오늘은 {{date}}입니다.", encoding="utf-8")

    with patch("app.bedrock._PROMPTS_DIR", tmp_path):
        from app.bedrock import _read_prompt_file, _load_prompt
        _read_prompt_file.cache_clear()
        result = _load_prompt("test_prompt", name="수진", date="2026-05-23")

    assert result == "안녕 수진, 오늘은 2026-05-23입니다."


def test_missing_variable_replaced_with_empty(tmp_path):
    """Unreferenced placeholders are replaced with empty string."""
    prompt_file = tmp_path / "test_missing.md"
    prompt_file.write_text("Hello {{name}} and {{unknown}}.", encoding="utf-8")

    with patch("app.bedrock._PROMPTS_DIR", tmp_path):
        from app.bedrock import _read_prompt_file, _load_prompt
        _read_prompt_file.cache_clear()
        result = _load_prompt("test_missing", name="테스트")

    assert result == "Hello 테스트 and ."


def test_cache_effect(tmp_path):
    """Same file content is cached (read only once)."""
    prompt_file = tmp_path / "test_cache.md"
    prompt_file.write_text("캐시 테스트 {{var}}", encoding="utf-8")

    with patch("app.bedrock._PROMPTS_DIR", tmp_path):
        from app.bedrock import _read_prompt_file, _load_prompt
        _read_prompt_file.cache_clear()

        result1 = _load_prompt("test_cache", var="첫 번째")
        # Modify file on disk — cached version should be used.
        prompt_file.write_text("변경된 내용 {{var}}", encoding="utf-8")
        result2 = _load_prompt("test_cache", var="두 번째")

    assert "캐시 테스트" in result1
    assert "캐시 테스트" in result2, "Cache should return original content"
