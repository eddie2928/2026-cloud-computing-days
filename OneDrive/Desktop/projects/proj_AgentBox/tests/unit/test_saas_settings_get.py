"""GET /api/settings/prompt-get, /api/settings/kb-ttl-get 단위 테스트."""
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("PROJECT_NAME", "agentbox")
    monkeypatch.setenv("ADMIN_TOKEN", "testtok")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def _mk_client(monkeypatch, get_item_response):
    mock_table = MagicMock()
    mock_table.get_item.return_value = get_item_response
    mock_db = MagicMock()
    mock_db.Table.return_value = mock_table

    import ec2.saas.server as srv
    monkeypatch.setattr(srv, "_dynamo", mock_db)
    monkeypatch.setattr(srv, "_ADMIN_TOKEN", "testtok")
    return TestClient(srv.app), mock_table


def test_get_prompt_returns_stored_value(monkeypatch):
    client, table = _mk_client(monkeypatch, {"Item": {"key": "bedrock_system_prompt", "value": "PROMPT_X"}})
    resp = client.get("/api/settings/prompt-get", headers={"X-Admin-Token": "testtok"})
    assert resp.status_code == 200
    assert resp.json() == {"system_prompt": "PROMPT_X"}


def test_get_prompt_returns_empty_when_missing(monkeypatch):
    client, _ = _mk_client(monkeypatch, {})  # no Item
    resp = client.get("/api/settings/prompt-get", headers={"X-Admin-Token": "testtok"})
    assert resp.status_code == 200
    assert resp.json() == {"system_prompt": ""}


def test_get_prompt_requires_token(monkeypatch):
    client, _ = _mk_client(monkeypatch, {})
    resp = client.get("/api/settings/prompt-get")
    assert resp.status_code == 401


def test_get_kb_ttl_returns_stored(monkeypatch):
    client, _ = _mk_client(monkeypatch, {"Item": {"key": "kb_ttl_minutes", "value": 7}})
    resp = client.get("/api/settings/kb-ttl-get", headers={"X-Admin-Token": "testtok"})
    assert resp.status_code == 200
    assert resp.json() == {"ttl_minutes": 7}


def test_get_kb_ttl_default_when_missing(monkeypatch):
    client, _ = _mk_client(monkeypatch, {})
    resp = client.get("/api/settings/kb-ttl-get", headers={"X-Admin-Token": "testtok"})
    assert resp.status_code == 200
    assert resp.json() == {"ttl_minutes": 5}  # default
