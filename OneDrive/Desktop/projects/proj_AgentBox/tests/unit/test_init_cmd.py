"""Unit tests for src/agentbox/init_cmd.py."""
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests as req_lib

import agentbox.init_cmd as init_module
from agentbox.init_cmd import init


@pytest.fixture(autouse=True)
def reset_logger():
    """Clear logger handlers before each test so _setup_file_logger runs fresh."""
    import logging
    logger = logging.getLogger("agentbox.init")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def fake_proj_root(tmp_path, monkeypatch):
    """Fake project root with required config files."""
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / ".sops.yaml").write_text("arn:aws:kms:us-east-1:123456:key/abc-real")
    (tmp_path / ".env.endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "encrypt_and_upload.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "logs").mkdir()
    return tmp_path


@pytest.fixture
def fake_src(tmp_path):
    src = tmp_path / "myproject"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")
    (src / "readme.md").write_text("# readme")
    (src / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return src


def test_init_invalid_dir(fake_proj_root):
    result = init("/nonexistent/path/that/does/not/exist")
    assert result == 2


def test_init_missing_sops_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    # No .sops.yaml in proj root
    (tmp_path / ".env.endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    src = tmp_path / "proj"
    src.mkdir()
    result = init(str(src))
    assert result == 3


def test_init_sops_yaml_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / ".sops.yaml").write_text("arn:aws:kms:{region}:123456:key/abc")
    (tmp_path / ".env.endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    src = tmp_path / "proj"
    src.mkdir()
    result = init(str(src))
    assert result == 3


def test_init_missing_env_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / ".sops.yaml").write_text("valid-arn")
    # No .env.endpoint
    src = tmp_path / "proj"
    src.mkdir()
    result = init(str(src))
    assert result == 3


def test_init_deps_missing_decline(fake_proj_root, fake_src, monkeypatch):
    monkeypatch.setattr(init_module, "check_dep", lambda dep: (False, "not found"))
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)
    with patch("builtins.input", return_value="n"):
        result = init(str(fake_src))
    assert result == 4


def test_init_deps_missing_accept(fake_proj_root, fake_src, monkeypatch):
    monkeypatch.setattr(init_module, "check_dep", lambda dep: (False, "not found"))
    monkeypatch.setattr(init_module, "try_auto_install", lambda dep: True)
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    mock_run = MagicMock()
    mock_run.return_value.returncode = 0

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("builtins.input", return_value="y"), \
         patch("agentbox.init_cmd.subprocess.run", return_value=mock_run.return_value), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        result = init(str(fake_src))
    assert result == 0


def test_init_encrypt_failure(fake_proj_root, fake_src, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("agentbox.init_cmd.subprocess.run", return_value=mock_result):
        result = init(str(fake_src), skip_deps=True)
    assert result == 5


def test_init_healthz_fail(fake_proj_root, fake_src, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("agentbox.init_cmd.subprocess.run", return_value=mock_result), \
         patch("agentbox.init_cmd.requests.get", side_effect=req_lib.ConnectionError("refused")):
        result = init(str(fake_src), skip_deps=True)
    assert result == 6


def test_init_tcp_fail(fake_proj_root, fake_src, monkeypatch, capsys):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.subprocess.run", return_value=mock_result), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection", side_effect=OSError("refused")):
        result = init(str(fake_src), skip_deps=True)
    assert result == 7


def test_init_success(fake_proj_root, fake_src, monkeypatch, capsys):
    monkeypatch.setattr(init_module, "get_terraform_output",
                        lambda name: "http://10.0.0.1:8000" if name == "saas_url" else None)

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.subprocess.run", return_value=mock_result), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        result = init(str(fake_src), skip_deps=True)

    assert result == 0
    captured = capsys.readouterr()
    assert "http://10.0.0.1:8000" in captured.out
