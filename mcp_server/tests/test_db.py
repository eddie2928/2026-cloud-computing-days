import os
import sys
import pytest


def test_async_session_local_is_callable():
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    from mcp_server.db import AsyncSessionLocal
    assert callable(AsyncSessionLocal)


def test_missing_database_url_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sys.modules.pop("mcp_server.db", None)
    with pytest.raises(KeyError):
        import mcp_server.db  # noqa: F401
