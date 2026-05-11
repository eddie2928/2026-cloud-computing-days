"""Integration test: Lambda handler -> MCP server (FastAPI in-process) - Task-4 API."""
import importlib
import importlib.util
import json
import pathlib
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

PROJECT = "agentbox"
REGION = "us-east-1"
ADMIN_TOKEN = "lambda-int-token"


def _load_lambda_handler():
    spec = importlib.util.spec_from_file_location(
        "mcp_bridge",
        pathlib.Path(__file__).parents[2] / "lambda" / "mcp_bridge.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler


@pytest.fixture
def lambda_mcp_stack(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", PROJECT)
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("MCP_ADMIN_TOKEN", ADMIN_TOKEN)

    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=f"{PROJECT}-encrypted-code")

        import ec2.mcp_server.server as mcp_module
        importlib.reload(mcp_module)
        mcp_test_client = TestClient(mcp_module.app)

        monkeypatch.setenv("MCP_SERVER_URL", "http://testserver")

        yield {"s3": s3, "mcp_client": mcp_test_client}


def test_lambda_to_mcp_decrypt_flow(lambda_mcp_stack, monkeypatch):
    """Lambda decrypt_and_stage -> MCP returns chunked FileChunk response."""
    s3 = lambda_mcp_stack["s3"]
    mcp_client = lambda_mcp_stack["mcp_client"]

    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/default/code.py.enc",
        Body=b"encrypted",
    )

    event = {
        "actionGroup": "decrypt_and_stage",
        "function": "decrypt_and_stage",
        "sessionId": "lambda-int-sess",
        "parameters": [
            {"name": "project_id", "value": "default"},
            {"name": "files", "value": "code.py"},
            {"name": "start_byte", "value": "0"},
            {"name": "max_bytes", "value": "20480"},
        ],
    }

    def fake_urlopen(req, timeout=None):
        path = req.get_full_url().replace("http://testserver", "")
        method = req.get_method()
        headers = dict(req.headers)

        if method == "POST":
            with patch("subprocess.run") as mock_sops:
                mock_sops.return_value.returncode = 0
                mock_sops.return_value.stdout = b"plaintext_code = True"
                response = mcp_client.post(
                    path, content=req.data,
                    headers={k: v for k, v in headers.items()},
                )
        else:
            response = mcp_client.request(method, path, headers=headers)

        mock_resp = MagicMock()
        mock_resp.read.return_value = response.content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    handler = _load_lambda_handler()
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = handler(event, None)

    assert "response" in result
    body_str = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    body = json.loads(body_str)
    assert "files" in body
    assert body["project_id"] == "default"
    assert body["files"][0]["content"] == "plaintext_code = True"


def test_lambda_to_mcp_list_files_flow(lambda_mcp_stack):
    """Lambda list_project_files -> MCP returns Markdown."""
    s3 = lambda_mcp_stack["s3"]
    mcp_client = lambda_mcp_stack["mcp_client"]

    s3.put_object(
        Bucket=f"{PROJECT}-encrypted-code",
        Key="encrypted_code/myproj/app.py.enc",
        Body=b"enc",
    )

    event = {
        "actionGroup": "list_project_files",
        "function": "list_project_files",
        "parameters": [{"name": "project_id", "value": "myproj"}],
    }

    def fake_urlopen(req, timeout=None):
        path = req.get_full_url().replace("http://testserver", "")
        headers = dict(req.headers)
        response = mcp_client.get(path, headers={k: v for k, v in headers.items()})
        mock_resp = MagicMock()
        mock_resp.read.return_value = response.content
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    handler = _load_lambda_handler()
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = handler(event, None)

    body_str = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    assert "app.py" in body_str
    assert "# Project files: myproj" in body_str


def test_bedrock_response_format(lambda_mcp_stack):
    """Verify Lambda returns correct Bedrock Action Group response format."""
    event = {
        "actionGroup": "decrypt_and_stage",
        "function": "decrypt_and_stage",
        "parameters": [
            {"name": "project_id", "value": "default"},
            {"name": "files", "value": "a.py"},
        ],
    }

    mock_mcp_response = {"project_id": "default", "files": []}

    handler = _load_lambda_handler()

    def mock_open(req, timeout=None):
        m = MagicMock()
        m.read.return_value = json.dumps(mock_mcp_response).encode()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        return m

    with patch("urllib.request.urlopen", side_effect=mock_open):
        result = handler(event, None)

    resp = result["response"]
    assert resp["actionGroup"] == "decrypt_and_stage"
    assert resp["function"] == "decrypt_and_stage"
    assert "functionResponse" in resp
    assert "TEXT" in resp["functionResponse"]["responseBody"]
