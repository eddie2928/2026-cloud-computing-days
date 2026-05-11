"""Integration tests for EC2 SaaS /audit HTML vs /api/audit JSON (ASGI in-process)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

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
def mock_dynamo(monkeypatch):
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}
    mock_db = MagicMock()
    mock_db.Table.return_value = mock_table

    import ec2.saas.server as srv
    monkeypatch.setattr(srv, "_dynamo", mock_db)
    monkeypatch.setattr(srv, "_ADMIN_TOKEN", "testtok")
    return mock_db


@pytest.fixture
def client(mock_dynamo):
    from ec2.saas.server import app
    return TestClient(app)


def test_audit_html_no_auth(client):
    resp = client.get("/audit")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert len(resp.text) > 0


def test_api_audit_requires_token(client):
    resp = client.get("/api/audit")
    assert resp.status_code == 401


def test_api_audit_with_token(client):
    resp = client.get("/api/audit", headers={"X-Admin-Token": "testtok"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_audit_html_serves_dist_when_present(client, tmp_path, monkeypatch):
    dist_file = tmp_path / "index.html"
    dist_file.write_text(
        "<html><head><title>AgentBox Dashboard</title></head><body>Loaded</body></html>",
        encoding="utf-8",
    )

    import ec2.saas.server as srv
    monkeypatch.setattr(srv, "_DASHBOARD_INDEX", dist_file)

    resp = client.get("/audit")
    assert resp.status_code == 200
    assert "Loaded" in resp.text
