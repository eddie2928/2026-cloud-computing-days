"""server.py 라우트가 /api/* prefix 로 정확히 등록되어 있는지 검증."""
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


@pytest.fixture
def client(monkeypatch):
    from unittest.mock import MagicMock
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}
    mock_table.get_item.return_value = {"Item": {"value": "stored"}}
    mock_db = MagicMock()
    mock_db.Table.return_value = mock_table

    import ec2.saas.server as srv
    monkeypatch.setattr(srv, "_dynamo", mock_db)
    monkeypatch.setattr(srv, "_ADMIN_TOKEN", "testtok")
    return TestClient(srv.app)


def test_api_pipeline_stream_ws_route_registered(client):
    """WebSocket /api/pipeline/stream 핸드셰이크 성공."""
    with client.websocket_connect("/api/pipeline/stream") as ws:
        # 핸드셰이크 성공 자체가 검증 — 메시지 송수신은 라이브에서.
        assert ws is not None


def test_api_settings_prompt_put_route(client):
    resp = client.put(
        "/api/settings/prompt",
        headers={"X-Admin-Token": "testtok"},
        json={"system_prompt": "test prompt"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_api_settings_kb_ttl_put_route(client):
    resp = client.put(
        "/api/settings/kb-ttl",
        headers={"X-Admin-Token": "testtok"},
        json={"ttl_minutes": 10},
    )
    assert resp.status_code == 200
    assert resp.json()["ttl_minutes"] == 10


def test_old_settings_paths_return_404(client):
    """이전 경로(`/settings/prompt`, `/settings/kb-ttl`)는 더 이상 동작하지 않음."""
    # SPA catch-all 은 GET 만 잡으므로 PUT 은 405 또는 404
    resp = client.put(
        "/settings/prompt",
        headers={"X-Admin-Token": "testtok"},
        json={"system_prompt": "x"},
    )
    assert resp.status_code in (404, 405)
