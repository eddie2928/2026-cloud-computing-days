"""Unit tests for set_cmd.py 7-step flow (Task-7 B2~B6)."""
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

import agentbox.set_cmd as set_module
from agentbox.set_cmd import run_set


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.set")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """Isolate HOME, USERPROFILE, _PROJ_ROOT, and AGENTBOX_HOME to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    (tmp_path / ".bashrc").write_text("", encoding="utf-8")
    monkeypatch.setattr(set_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir(exist_ok=True)
    return tmp_path


class FakeArgs:
    def __init__(self, yes=False, skip_deps_install=False):
        self.yes = yes
        self.skip_deps_install = skip_deps_install


def _all_deps_ok(monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)


# ── T1: 전체 7단계 통과, exit 0 ──────────────────────────────────────────────
def test_all_steps_pass(tmp_home, monkeypatch):
    _all_deps_ok(monkeypatch)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    with patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs(yes=True))

    assert rc == 0


# ── T2: sops 없음 + -y → 자동 설치 mock 호출 ─────────────────────────────────
def test_missing_dep_auto_install(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (False, "not found"))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)
    install_calls = []
    monkeypatch.setattr(set_module, "try_auto_install", lambda d: install_calls.append(d.name) or True)

    with patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs(yes=True))

    assert rc == 0
    assert len(install_calls) > 0


# ── T3: sops 없음 + -y 없음 → exit 4 ─────────────────────────────────────────
def test_missing_dep_no_autoinstall_returns_4(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (False, "not found"))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    with patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs(yes=False))

    assert rc == 4


# ── T4: CA 없음 → gen_mtls_certs 호출, Phase 4 OK ────────────────────────────
def test_ca_generated_when_missing(tmp_home, monkeypatch):
    _all_deps_ok(monkeypatch)

    gen_calls = []

    def fake_gen_mtls(certs_dir):
        gen_calls.append(certs_dir)
        ca_crt = certs_dir / "agentbox-ca.crt"
        ca_key = certs_dir / "agentbox-ca.key"
        ep_crt = certs_dir / "endpoint.crt"
        ep_key = certs_dir / "endpoint.key"
        for p in (ca_crt, ca_key, ep_crt, ep_key):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"FAKE")
        return ca_crt, ca_key, ep_crt, ep_key

    with patch("agentbox.set_cmd.subprocess.run", return_value=MagicMock(returncode=1)), \
         patch("agentbox.proxy.ca.gen_mtls_certs", fake_gen_mtls), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs(yes=True))

    assert rc == 0
    assert len(gen_calls) == 1


# ── T5: proto stub 없음 → protoc mock 호출 ───────────────────────────────────
def test_proto_stub_missing_calls_protoc(tmp_home, monkeypatch):
    _all_deps_ok(monkeypatch)

    # Make proto file exist
    proto_dir = tmp_home / "grpc"
    proto_dir.mkdir()
    (proto_dir / "inspect.proto").write_text("syntax='proto3';")

    protoc_calls = []

    def fake_run(cmd, *a, **kw):
        if "grpc_tools.protoc" in " ".join(str(c) for c in cmd):
            protoc_calls.append(cmd)
            return MagicMock(returncode=0)
        return MagicMock(returncode=0)

    import importlib
    orig_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else None

    with patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd.subprocess.run", side_effect=fake_run), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"), \
         patch("importlib.import_module", side_effect=ImportError("no stub")):
        rc = run_set(FakeArgs(yes=True))

    assert len(protoc_calls) > 0


# ── T6 (B3): :8080 LISTEN 안 됨 → log 끝 50줄 출력, exit 7 ──────────────────
def test_run_log_dump(tmp_home, monkeypatch):
    _all_deps_ok(monkeypatch)

    log_content = "\n".join(f"line {i}" for i in range(60))

    def fake_popen(cmd, **kw):
        # Write fake log content
        logfile = kw.get("stdout")
        if logfile and hasattr(logfile, "write"):
            logfile.write(log_content)
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        return mock_proc

    printed = []

    def fake_log(msg, level="info"):
        printed.append(msg)
        getattr(__import__("logging").getLogger("agentbox.set"), level)(msg)

    import socket as _socket

    def fake_connect(addr, timeout=None):
        raise OSError("not listening")

    with patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd.subprocess.Popen", side_effect=fake_popen), \
         patch("agentbox.set_cmd.socket.create_connection", side_effect=fake_connect), \
         patch("agentbox.set_cmd.time.sleep"), \
         patch("agentbox.set_cmd.time.monotonic", side_effect=[0, 11, 11]), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"), \
         patch("agentbox.set_cmd._log", side_effect=fake_log):
        rc = run_set(FakeArgs(yes=True))

    assert rc == 7
    # Verify error message about LISTEN failure appeared
    assert any("LISTEN" in m or "ERROR" in m for m in printed)


# ── T7 (B4): gRPC TCP fail → _check_grpc_tcp returns 7 + 가이드 메시지 ────────
def test_grpc_connect_fail(tmp_home, monkeypatch):
    """_check_grpc_tcp returns 7 when TCP connect fails, with guide message."""
    from agentbox.set_cmd import _check_grpc_tcp
    import agentbox.config as cfg_mod

    printed = []
    monkeypatch.setattr(set_module, "_log", lambda msg, level="info": printed.append(msg))

    with patch("agentbox.set_cmd.socket.create_connection", side_effect=OSError("refused")):
        # Patch cfg instance GRPC_HOST directly
        orig = cfg_mod.cfg.GRPC_HOST
        cfg_mod.cfg.GRPC_HOST = "10.0.0.1"
        try:
            rc = _check_grpc_tcp()
        finally:
            cfg_mod.cfg.GRPC_HOST = orig

    assert rc == 7
    assert any("보안 그룹" in m or "TCP" in m or "50051" in m for m in printed)


# ── T8 (B6): mTLS handshake 실패 → _check_mtls_handshake returns 7 ───────────
def test_mtls_handshake_fail(tmp_home, monkeypatch):
    """_check_mtls_handshake returns 7 with CA/cert guidance when handshake fails."""
    from agentbox.set_cmd import _check_mtls_handshake
    from agentbox.dotagentbox import ensure_layout
    import agentbox.config as cfg_mod

    layout = ensure_layout(tmp_home)
    printed = []
    monkeypatch.setattr(set_module, "_log", lambda msg, level="info": printed.append(msg))

    with patch("agentbox.grpc.handshake.verify_mtls_handshake",
               return_value=(False, "CA mismatch")):
        orig = cfg_mod.cfg.GRPC_HOST
        cfg_mod.cfg.GRPC_HOST = "10.0.0.1"
        try:
            rc = _check_mtls_handshake(layout)
        finally:
            cfg_mod.cfg.GRPC_HOST = orig

    assert rc == 7
    assert any("CA" in m or "cert" in m.lower() for m in printed)
