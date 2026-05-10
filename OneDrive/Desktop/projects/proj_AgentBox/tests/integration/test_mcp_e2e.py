"""Integration test: MCP server end-to-end with real sops binary (if available)."""
import os
import shutil
import pytest
from unittest.mock import patch
from moto import mock_aws
import boto3
from fastapi.testclient import TestClient


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
        s3.create_bucket(Bucket=f"{PROJECT}-kb-staging")

        import importlib
        import ec2.mcp_server.server as mcp_module
        importlib.reload(mcp_module)

        yield TestClient(mcp_module.app), s3


def test_healthz(mcp_e2e_client):
    client, _ = mcp_e2e_client
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "service": "mcp"}


def test_decrypt_stage_and_cleanup_flow(mcp_e2e_client):
    """Full flow: upload encrypted file -> decrypt_and_stage -> cleanup -> verify empty."""
    client, s3 = mcp_e2e_client

    sops_available = shutil.which("sops") is not None

    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/default/main.py.enc",
        Body=b"fake-sops-encrypted",
    )

    if sops_available:
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "default", "session_id": "e2e-sess"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    else:
        pytest.skip("sops binary not available - skipping real decrypt test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["prefix"].startswith("staging/e2e-sess/")

    cleanup = client.delete(
        "/mcp/cleanup/e2e-sess",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert cleanup.status_code == 200
    assert cleanup.json()["deleted"] >= 1

    objs = s3.list_objects_v2(Bucket=f"{PROJECT}-kb-staging", Prefix="staging/e2e-sess/")
    assert len(objs.get("Contents", [])) == 0


def test_decrypt_stage_with_mocked_sops(mcp_e2e_client):
    """Full flow with mocked sops: verify cleanup leaves kb-staging empty."""
    client, s3 = mcp_e2e_client

    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/testproj/app.py.enc",
        Body=b"sops-encrypted-content",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = b"decrypted_code = True"

        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "testproj", "session_id": "int-sess-1"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )

    assert resp.status_code == 200

    cleanup = client.delete(
        "/mcp/cleanup/int-sess-1",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert cleanup.json()["deleted"] == 1

    objs = s3.list_objects_v2(Bucket=f"{PROJECT}-kb-staging", Prefix="staging/int-sess-1/")
    assert len(objs.get("Contents", [])) == 0
