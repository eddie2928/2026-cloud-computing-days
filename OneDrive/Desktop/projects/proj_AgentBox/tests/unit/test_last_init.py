"""Unit tests for src/agentbox/last_init.py."""
from pathlib import Path

import pytest

from agentbox import last_init


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.last_init")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


def test_write_then_read_roundtrip(tmp_path):
    meta = {
        "project_id": "myrepo",
        "src_path": "/home/user/myrepo",
        "s3_uri": "s3://bucket/encrypted_code/myrepo/",
        "uploaded_at": "2026-05-11T00:00:00+00:00",
        "saas_url": "http://10.0.0.1:8000",
    }
    path = tmp_path / "last_init.json"
    last_init.write(meta, path=path)
    result = last_init.read(path=path)
    assert result == meta


def test_read_missing_returns_none(tmp_path):
    path = tmp_path / "nonexistent.json"
    result = last_init.read(path=path)
    assert result is None


def test_read_corrupted_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not valid json !!!", encoding="utf-8")
    result = last_init.read(path=path)
    assert result is None


def test_atomic_write_no_tmp_residual(tmp_path):
    meta = {"project_id": "test"}
    path = tmp_path / "last_init.json"
    last_init.write(meta, path=path)

    tmp_file = path.with_suffix(".tmp")
    assert not tmp_file.exists()
    assert path.exists()


def test_write_creates_parent_dir(tmp_path):
    meta = {"project_id": "test"}
    path = tmp_path / "nested" / "dir" / "last_init.json"
    last_init.write(meta, path=path)
    assert path.exists()
    assert last_init.read(path=path) == meta
