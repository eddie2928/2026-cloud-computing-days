"""Integration test: MCP server e2e with new Task-4 API (chunked, no kb_staging)."""
import importlib
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
ADMIN_TOKEN = "e2e-test-token"


@pytest.fixture
def mcp_e2e_client(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", PROJECT)
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)

    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=f"{PROJECT}-encrypted-code")

        import ec2.mcp_server.server as mcp_module
        importlib.reload(mcp_module)

        yield TestClient(mcp_module.app), s3


def test_healthz(mcp_e2e_client):
    client, _ = mcp_e2e_client
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "service": "mcp"}


def test_list_and_decrypt_flow(mcp_e2e_client):
    """list_files then decrypt_and_stage returns inline content."""
    client, s3 = mcp_e2e_client

    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/testproj/app.py.enc",
        Body=b"sops-encrypted-content",
    )

    # List files
    resp = client.get(
        "/mcp/list_files/testproj",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200
    assert "app.py" in resp.text

    # Decrypt
    plaintext = b"decrypted_code = True"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = plaintext

        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "testproj", "files": ["app.py"]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["files"][0]["content"] == "decrypted_code = True"
    assert data["files"][0]["is_binary"] is False


def test_no_cleanup_endpoint(mcp_e2e_client):
    """Verify /mcp/cleanup endpoint is gone in Task-4."""
    client, _ = mcp_e2e_client
    resp = client.delete(
        "/mcp/cleanup/some-session",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 404
