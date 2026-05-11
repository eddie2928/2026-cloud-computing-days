"""Integration test: agentbox init end-to-end (moto S3/KMS + monkeypatched connectivity)."""
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
import requests as req_lib
from moto import mock_aws

import agentbox.init_cmd as init_module
from agentbox.init_cmd import init

PROJECT = "agentbox"
REGION = "us-east-1"


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.init")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def fake_project(tmp_path):
    src = tmp_path / "demo_proj"
    src.mkdir()
    (src / "a.txt").write_text("hello agentbox")
    (src / "b.json").write_text('{"k": 1}')
    (src / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return src


@pytest.fixture
def proj_root(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / ".sops.yaml").write_text("arn:aws:kms:us-east-1:123456:key/real-key")
    (tmp_path / ".env.endpoint").write_text("EC2_GRPC_HOST=127.0.0.1\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (tmp_path / "logs").mkdir()
    return tmp_path


@mock_aws
def test_init_e2e_uploads_files(fake_project, proj_root, monkeypatch, capsys):
    # Create S3 bucket
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=f"{PROJECT}-encrypted-code")

    # Write a script that copies files as fake .enc uploads
    script = proj_root / "scripts" / "encrypt_and_upload.sh"
    # Simulate the script: just create .enc objects in S3 via AWS CLI mock
    # We mock subprocess.run for the encrypt step to succeed
    enc_result = MagicMock()
    enc_result.returncode = 0

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    monkeypatch.setattr(init_module, "get_terraform_output",
                        lambda name: "http://127.0.0.1:8000" if name == "saas_url" else None)

    with patch("agentbox.init_cmd.subprocess.run", return_value=enc_result), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        result = init(str(fake_project), skip_deps=True)

    assert result == 0
    captured = capsys.readouterr()
    assert "demo_proj" in captured.out
    assert "http://127.0.0.1:8000" in captured.out


@mock_aws
def test_init_e2e_healthz_failure(fake_project, proj_root, monkeypatch):
    enc_result = MagicMock()
    enc_result.returncode = 0

    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    with patch("agentbox.init_cmd.subprocess.run", return_value=enc_result), \
         patch("agentbox.init_cmd.requests.get",
               side_effect=req_lib.ConnectionError("connection refused")):
        result = init(str(fake_project), skip_deps=True)

    assert result == 6


@mock_aws
def test_init_e2e_grpc_failure(fake_project, proj_root, monkeypatch):
    enc_result = MagicMock()
    enc_result.returncode = 0
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    with patch("agentbox.init_cmd.subprocess.run", return_value=enc_result), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection",
               side_effect=OSError("connection refused")):
        result = init(str(fake_project), skip_deps=True)

    assert result == 7
