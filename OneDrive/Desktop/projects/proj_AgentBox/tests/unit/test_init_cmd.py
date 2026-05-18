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
    import logging
    logger = logging.getLogger("agentbox.init")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def fake_proj_root(tmp_path, monkeypatch):
    """Fake project root with config at AGENTBOX_HOME (new layout)."""
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    # Set AGENTBOX_HOME so _global_home() returns a temp dir
    global_home = tmp_path / "global"
    global_home.mkdir()
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    # Create required config files
    (global_home / "sops.yaml").write_text("arn:aws:kms:us-east-1:123456:key/abc-real")
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    certs_dir = global_home / "certs" / "grpc"
    certs_dir.mkdir(parents=True)
    (certs_dir / "endpoint.crt").write_text("FAKE")
    (certs_dir / "endpoint.key").write_text("FAKE")
    (certs_dir / "agentbox-ca.crt").write_text("FAKE")
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
    global_home = tmp_path / "global"
    global_home.mkdir()
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    # No sops.yaml in global home
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    src = tmp_path / "proj"
    src.mkdir()
    result = init(str(src))
    assert result == 3


def test_init_sops_yaml_placeholder(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    global_home = tmp_path / "global"
    global_home.mkdir()
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    (global_home / "sops.yaml").write_text("arn:aws:kms:{region}:123456:key/abc")
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    src = tmp_path / "proj"
    src.mkdir()
    result = init(str(src))
    assert result == 3


def test_init_missing_env_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    global_home = tmp_path / "global"
    global_home.mkdir()
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    (global_home / "sops.yaml").write_text("valid-arn")
    # No endpoint file
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

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("builtins.input", return_value="y"), \
         patch("agentbox.init_cmd.encrypt_local", return_value=fake_src / "enc"), \
         patch("agentbox.init_cmd.upload_via_ec2"), \
         patch("agentbox.init_cmd.shutil.rmtree"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        result = init(str(fake_src))
    assert result == 0


def test_init_encrypt_failure(fake_proj_root, fake_src, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)
    import subprocess

    with patch("agentbox.init_cmd.encrypt_local",
               side_effect=subprocess.CalledProcessError(5, "sops", stderr="KMS error")):
        result = init(str(fake_src), skip_deps=True)
    assert result == 5


def test_init_healthz_fail(fake_proj_root, fake_src, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    with patch("agentbox.init_cmd.encrypt_local", return_value=fake_src / "enc"), \
         patch("agentbox.init_cmd.upload_via_ec2"), \
         patch("agentbox.init_cmd.shutil.rmtree"), \
         patch("agentbox.init_cmd.requests.get", side_effect=req_lib.ConnectionError("refused")):
        result = init(str(fake_src), skip_deps=True)
    assert result == 6


def test_init_tcp_fail(fake_proj_root, fake_src, monkeypatch, capsys):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.encrypt_local", return_value=fake_src / "enc"), \
         patch("agentbox.init_cmd.upload_via_ec2"), \
         patch("agentbox.init_cmd.shutil.rmtree"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection", side_effect=OSError("refused")):
        result = init(str(fake_src), skip_deps=True)
    assert result == 7


def test_init_success(fake_proj_root, fake_src, monkeypatch, capsys):
    monkeypatch.setattr(init_module, "get_terraform_output",
                        lambda name: "http://10.0.0.1:8000" if name == "saas_url" else None)

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.encrypt_local", return_value=fake_src / "enc"), \
         patch("agentbox.init_cmd.upload_via_ec2"), \
         patch("agentbox.init_cmd.shutil.rmtree"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        result = init(str(fake_src), skip_deps=True)

    assert result == 0
    captured = capsys.readouterr()
    assert "http://10.0.0.1:8000" in captured.out
