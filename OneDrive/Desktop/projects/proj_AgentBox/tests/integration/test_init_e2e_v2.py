"""Integration tests for agentbox init end-to-end (Task-7 J2)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setattr(init_module, "_PROJ_ROOT", tmp_path)
    global_home = tmp_path / "global"
    global_home.mkdir()
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    (global_home / "sops.yaml").write_text("creation_rules:\n  - kms: arn:aws:kms:us-east-1:123:key/real\n")
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=10.0.0.1\n")
    return tmp_path


@pytest.fixture
def src_dir(isolated_env):
    src = isolated_env / "myrepo"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")
    return src


# ── T1: init 성공 → exit 0, last_init.json 생성 ──────────────────────────────
def test_init_e2e_success(isolated_env, src_dir, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output",
                        lambda name: "http://10.0.0.1:8000" if name == "saas_url" else None)

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.encrypt_and_upload"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection"):
        rc = init(str(src_dir), skip_deps=True)

    assert rc == 0
    # last_init.json should be in local state
    last_init_path = isolated_env / ".agentbox" / "last_init.json"
    assert last_init_path.exists()


# ── T2: /healthz 502 → exit 6 ────────────────────────────────────────────────
def test_init_e2e_healthz_fail(isolated_env, src_dir, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)
    mock_resp = MagicMock()
    mock_resp.status_code = 502

    with patch("agentbox.init_cmd.encrypt_and_upload"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp):
        rc = init(str(src_dir), skip_deps=True)

    assert rc == 6


# ── T3: gRPC TCP fail → exit 7 ───────────────────────────────────────────────
def test_init_e2e_grpc_fail(isolated_env, src_dir, monkeypatch):
    monkeypatch.setattr(init_module, "get_terraform_output", lambda _: None)
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.init_cmd.encrypt_and_upload"), \
         patch("agentbox.init_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.init_cmd.socket.create_connection",
               side_effect=OSError("refused")):
        rc = init(str(src_dir), skip_deps=True)

    assert rc == 7
