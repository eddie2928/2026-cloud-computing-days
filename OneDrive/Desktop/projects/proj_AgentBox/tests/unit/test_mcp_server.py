"""Unit tests for ec2/mcp_server/server.py - updated for Task-4 new API."""
import importlib
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
ADMIN_TOKEN = "test-token"


@pytest.fixture
def mcp_client(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", PROJECT)
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)

    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=f"{PROJECT}-encrypted-code")

        import ec2.mcp_server.server as mcp_module
        importlib.reload(mcp_module)

        yield TestClient(mcp_module.app), s3


def test_healthz_no_auth(mcp_client):
    client, _ = mcp_client
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["service"] == "mcp"


def test_admin_token_required(mcp_client):
    client, _ = mcp_client
    resp = client.post(
        "/mcp/decrypt_and_stage",
        json={"project_id": "default", "files": ["a.txt"]},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_decrypt_empty_files_422(mcp_client):
    client, _ = mcp_client
    resp = client.post(
        "/mcp/decrypt_and_stage",
        json={"project_id": "default", "files": []},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 422


def test_decrypt_file_not_found(mcp_client):
    client, _ = mcp_client
    resp = client.post(
        "/mcp/decrypt_and_stage",
        json={"project_id": "nonexistent", "files": ["missing.py"]},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["files"][0]["error"] == "not_found"


def test_decrypt_and_stage_happy_path(mcp_client):
    client, s3 = mcp_client
    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/default/code.py.enc",
        Body=b"fake-encrypted-content",
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = b"plaintext_code = 'hello'"
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "default", "files": ["code.py"]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "default"
    assert len(data["files"]) == 1
    assert "plaintext_code" in data["files"][0]["content"]


def test_cleanup_endpoint_removed(mcp_client):
    """Verify /mcp/cleanup endpoint no longer exists in Task-4."""
    client, _ = mcp_client
    resp = client.delete(
        "/mcp/cleanup/some-session",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 404
