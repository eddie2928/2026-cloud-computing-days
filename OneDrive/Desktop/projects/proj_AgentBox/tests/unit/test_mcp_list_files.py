"""Unit tests for GET /mcp/list_files/{project_id} endpoint."""
import importlib
from datetime import datetime, timezone

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
ADMIN_TOKEN = "list-test-token"


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


def _auth():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def test_list_empty(mcp_client):
    client, _ = mcp_client
    resp = client.get("/mcp/list_files/emptyproj", headers=_auth())
    assert resp.status_code == 200
    assert "Total: 0 files" in resp.text


def test_list_three_text_files(mcp_client):
    client, s3 = mcp_client
    for name in ["src/main.py.enc", "README.md.enc", "config.json.enc"]:
        s3.put_object(
            Bucket=f"{PROJECT}-encrypted-code",
            Key=f"encrypted_code/proj1/{name}",
            Body=b"encrypted",
        )
    resp = client.get("/mcp/list_files/proj1", headers=_auth())
    assert resp.status_code == 200
    body = resp.text
    assert "Total: 3 files" in body
    # All text extensions → is_binary false
    assert body.count("| false |") == 3
    assert "src/main.py" in body
    assert "README.md" in body
    assert "config.json" in body


def test_list_with_binary_extensions(mcp_client):
    client, s3 = mcp_client
    for name in ["image.png.enc", "archive.zip.enc", "doc.pdf.enc"]:
        s3.put_object(
            Bucket=f"{PROJECT}-encrypted-code",
            Key=f"encrypted_code/binproj/{name}",
            Body=b"encrypted",
        )
    resp = client.get("/mcp/list_files/binproj", headers=_auth())
    assert resp.status_code == 200
    body = resp.text
    assert "Total: 3 files" in body
    assert body.count("| true |") == 3


def test_list_paginated(mcp_client):
    """1500 objects should all appear via paginator."""
    client, s3 = mcp_client
    for i in range(1500):
        s3.put_object(
            Bucket=f"{PROJECT}-encrypted-code",
            Key=f"encrypted_code/bigproj/file{i:04d}.py.enc",
            Body=b"x",
        )
    resp = client.get("/mcp/list_files/bigproj", headers=_auth())
    assert resp.status_code == 200
    assert "Total: 1500 files" in resp.text


def test_list_unknown_project(mcp_client):
    client, _ = mcp_client
    resp = client.get("/mcp/list_files/unknownproj", headers=_auth())
    assert resp.status_code == 200
    assert "Total: 0 files" in resp.text
