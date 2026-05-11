"""Integration test: MCP full flow v2 with real sops binary (if available)."""
import importlib
import shutil
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
ADMIN_TOKEN = "fullflow-v2-token"


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


def _upload_enc(s3, pid, rel_path, body=b"fake-enc"):
    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key=f"encrypted_code/{pid}/{rel_path}.enc",
        Body=body,
    )


def _mock_sops(plaintext: bytes):
    m = MagicMock()
    m.returncode = 0
    m.stdout = plaintext
    return m


def test_list_then_decrypt_text(mcp_client):
    """list_files -> decrypt_and_stage for text file."""
    client, s3 = mcp_client
    _upload_enc(s3, "proj", "src/main.py")
    _upload_enc(s3, "proj", "config.yaml")

    # Step 1: list files
    resp = client.get("/mcp/list_files/proj", headers=_auth())
    assert resp.status_code == 200
    body = resp.text
    assert "src/main.py" in body
    assert "config.yaml" in body

    # Step 2: decrypt text files
    content_py = b"def main(): pass"
    content_yaml = b"key: value"
    sops_results = [_mock_sops(content_py), _mock_sops(content_yaml)]

    with patch("subprocess.run", side_effect=sops_results):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "proj", "files": ["src/main.py", "config.yaml"],
                  "start_byte": 0, "max_bytes": 20480},
            headers=_auth(),
        )
    assert resp.status_code == 200
    data = resp.json()
    files = {f["path"]: f for f in data["files"]}
    assert files["src/main.py"]["content"] == "def main(): pass"
    assert files["config.yaml"]["content"] == "key: value"
    assert files["src/main.py"]["is_binary"] is False


def test_list_with_binary_and_text(mcp_client):
    """Binary files return is_binary=true, content=null."""
    client, s3 = mcp_client
    _upload_enc(s3, "mixed", "script.py")
    _upload_enc(s3, "mixed", "image.png")

    text_content = b"print('hello')"
    binary_content = b"\x00\x01\x02\x03" * 100

    sops_results = [_mock_sops(text_content), _mock_sops(binary_content)]
    with patch("subprocess.run", side_effect=sops_results):
        resp = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "mixed", "files": ["script.py", "image.png"]},
            headers=_auth(),
        )
    data = resp.json()
    files = {f["path"]: f for f in data["files"]}
    assert files["script.py"]["is_binary"] is False
    assert files["script.py"]["content"] == "print('hello')"
    assert files["image.png"]["is_binary"] is True
    assert files["image.png"]["content"] is None


def test_chunked_large_file(mcp_client):
    """50KB text: 1st chunk truncated, 2nd chunk completes it."""
    client, s3 = mcp_client
    _upload_enc(s3, "big", "large.txt")

    plaintext = b"X" * 50000

    # First call
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp1 = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "big", "files": ["large.txt"],
                  "start_byte": 0, "max_bytes": 20480},
            headers=_auth(),
        )
    chunk1 = resp1.json()["files"][0]
    assert chunk1["truncated"] is True
    assert chunk1["next_offset"] == 20480

    # Second call
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp2 = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "big", "files": ["large.txt"],
                  "start_byte": chunk1["next_offset"], "max_bytes": 20480},
            headers=_auth(),
        )
    chunk2 = resp2.json()["files"][0]
    assert chunk2["truncated"] is True  # still more (50000 > 2*20480)
    assert chunk2["next_offset"] == 40960

    # Third call - remainder
    with patch("subprocess.run", return_value=_mock_sops(plaintext)):
        resp3 = client.post(
            "/mcp/decrypt_and_stage",
            json={"project_id": "big", "files": ["large.txt"],
                  "start_byte": chunk2["next_offset"], "max_bytes": 20480},
            headers=_auth(),
        )
    chunk3 = resp3.json()["files"][0]
    assert chunk3["truncated"] is False

    # Concatenated content matches original
    combined = chunk1["content"] + chunk2["content"] + chunk3["content"]
    assert combined == "X" * 50000


def test_healthz_still_works(mcp_client):
    client, _ = mcp_client
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "service": "mcp"}


def test_no_cleanup_endpoint(mcp_client):
    """Verify /mcp/cleanup endpoint no longer exists."""
    client, _ = mcp_client
    resp = client.delete("/mcp/cleanup/some-session", headers=_auth())
    assert resp.status_code == 404
