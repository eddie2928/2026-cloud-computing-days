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
    global_home = tmp_path / "global"
    global_home.mkdir()
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    (global_home / "sops.yaml").write_text("arn:aws:kms:us-east-1:123456:key/real-key")
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=127.0.0.1\n")
    return tmp_path


@mock_aws
def test_init_e2e_uploads_files(fake_project, proj_root, monkeypatch, capsys):
    monkeypatch.setattr(init_module, "get_terraform_output",
                        lambda name: "http://127.0.0.1:8000" if name == "saas_url" else None)

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.encrypt_and_upload"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        result = init(str(fake_project), skip_deps=True)

    assert result == 0
    captured = capsys.readouterr()
    assert "demo_proj" in captured.out
    assert "http://127.0.0.1:8000" in captured.out


@mock_aws
def test_init_e2e_healthz_failure(fake_project, proj_root, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    with patch("agentbox.init_cmd.encrypt_and_upload"), \
         patch("agentbox.init_cmd.requests.get",
               side_effect=req_lib.ConnectionError("connection refused")):
        result = init(str(fake_project), skip_deps=True)

    assert result == 6


@mock_aws
def test_init_e2e_grpc_failure(fake_project, proj_root, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    with patch("agentbox.init_cmd.encrypt_and_upload"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection",
               side_effect=OSError("connection refused")):
        result = init(str(fake_project), skip_deps=True)

    assert result == 7
