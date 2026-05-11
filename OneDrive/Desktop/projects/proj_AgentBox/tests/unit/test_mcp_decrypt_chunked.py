"""Unit tests for POST /mcp/decrypt_and_stage (chunked, Zero-Knowledge)."""
import importlib
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
ADMIN_TOKEN = "decrypt-test-token"


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


def _upload_enc(s3, project_id, rel_path):
    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key=f"encrypted_code/{project_id}/{rel_path}.enc",
        Body=b"sops-encrypted",
    )


def _mock_sops(plaintext: bytes):
    m = MagicMock()
    m.returncode = 0
    m.stdout = plaintext
    return m


def test_text_single_full(mcp_client):
    client, s3 = mcp_client
    _upload_enc(s3, "p1", "a.txt")
    plaintext = b"A" * 1024
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "p1", "files": ["a.txt"], "start_byte": 0, "max_bytes": 20480},
            headers=_auth(),
        )
    assert resp.status_code == 200
    chunk = resp.json()["files"][0]
    assert chunk["truncated"] is False
    assert chunk["next_offset"] is None
    assert chunk["returned_bytes"] == 1024
    assert len(chunk["content"]) == 1024


def test_text_chunked_first(mcp_client):
    client, s3 = mcp_client
    _upload_enc(s3, "p2", "big.txt")
    plaintext = b"B" * 30000
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "p2", "files": ["big.txt"], "start_byte": 0, "max_bytes": 20480},
            headers=_auth(),
        )
    chunk = resp.json()["files"][0]
    assert chunk["returned_bytes"] == 20480
    assert chunk["truncated"] is True
    assert chunk["next_offset"] == 20480


def test_text_chunked_second(mcp_client):
    client, s3 = mcp_client
    _upload_enc(s3, "p3", "big.txt")
    plaintext = b"C" * 30000
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "p3", "files": ["big.txt"], "start_byte": 20480, "max_bytes": 20480},
            headers=_auth(),
        )
    chunk = resp.json()["files"][0]
    assert chunk["returned_bytes"] == 9520
    assert chunk["truncated"] is False
    assert chunk["next_offset"] is None


def test_binary_file(mcp_client):
    client, s3 = mcp_client
    _upload_enc(s3, "p4", "img.bin")
    plaintext = b"\x00\x01\x02\x03" * 256
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "p4", "files": ["img.bin"]},
            headers=_auth(),
        )
    chunk = resp.json()["files"][0]
    assert chunk["is_binary"] is True
    assert chunk["content"] is None
    assert chunk["size"] == len(plaintext)


def test_decrypt_failure(mcp_client):
    client, s3 = mcp_client
    _upload_enc(s3, "p5", "bad.py")
    fail = MagicMock()
    fail.returncode = 1
    fail.stderr = b"MAC mismatch"
    with patch("subprocess.run", return_value=fail):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "p5", "files": ["bad.py"]},
            headers=_auth(),
        )
    chunk = resp.json()["files"][0]
    assert "decrypt_failed" in chunk["error"]


def test_file_not_found(mcp_client):
    client, s3 = mcp_client
    _upload_enc(s3, "p6", "good.py")
    plaintext = b"print('ok')"
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "p6", "files": ["good.py", "missing.py"]},
            headers=_auth(),
        )
    data = resp.json()
    files = {f["path"]: f for f in data["files"]}
    assert files["good.py"]["error"] is None
    assert files["missing.py"]["error"] == "not_found"
