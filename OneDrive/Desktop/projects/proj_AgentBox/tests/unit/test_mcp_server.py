"""Unit tests for ec2/mcp_server/server.py using moto + FastAPI TestClient."""
import os
import pytest
from unittest.mock import patch
from moto import mock_aws
import boto3
from fastapi.testclient import TestClient


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
        s3.create_bucket(Bucket=f"{PROJECT}-kb-staging")

        import importlib
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
        json={"project_id": "default", "session_id": "s1"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_decrypt_no_files_404(mcp_client):
    client, _ = mcp_client
    resp = client.post(
        "/mcp/decrypt_and_stage",
        json={"project_id": "nonexistent", "session_id": "s1"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 404


def test_decrypt_and_stage_happy_path(mcp_client):
    client, s3 = mcp_client
    # Upload a fake encrypted file
    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/default/code.py.enc",
        Body=b"fake-encrypted-content",
    )
    # Mock sops subprocess to return plaintext
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = b"plaintext_code = 'hello'"
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "default", "session_id": "sess-001"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kb_bucket"] == f"{PROJECT}-kb-staging"
    assert "staging/sess-001/" in data["prefix"]

    # Verify the file was uploaded to kb-staging
    objs = s3.list_objects_v2(Bucket=f"{PROJECT}-kb-staging", Prefix="staging/sess-001/")
    assert len(objs.get("Contents", [])) >= 1


def test_cleanup_deletes_objects(mcp_client):
    client, s3 = mcp_client
    # Pre-populate kb-staging with 3 objects
    for i in range(3):
        s3.put_object(
            Bucket=f"{PROJECT}-kb-staging",
            Key=f"staging/sess-del/file{i}.py",
            Body=b"content",
        )
    resp = client.delete(
        "/mcp/cleanup/sess-del",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 3

    objs = s3.list_objects_v2(Bucket=f"{PROJECT}-kb-staging", Prefix="staging/sess-del/")
    assert len(objs.get("Contents", [])) == 0
