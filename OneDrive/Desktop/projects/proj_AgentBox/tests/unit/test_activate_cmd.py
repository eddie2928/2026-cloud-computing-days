"""Unit tests for agentbox._activate on/off eval-pattern commands (Task-7 C1)."""
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import agentbox._activate as activate_mod


@pytest.fixture
def tmp_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    monkeypatch.setattr(activate_mod, "_PROJ_ROOT", tmp_path)
    return tmp_path


# ── T1: _on stdout에 export 3줄 포함 ─────────────────────────────────────────
def test_on_stdout_exports(tmp_layout, capsys):
    with patch("agentbox._activate._is_listening", return_value=True):
        from agentbox._activate import on_command
        rc = on_command(project_root=tmp_layout)

    out = capsys.readouterr().out
    assert "export HTTPS_PROXY=http://127.0.0.1:" in out
    assert "export NO_PROXY=" in out
    assert "export NODE_EXTRA_CA_CERTS=" in out
    assert rc == 0


# ── T2: :8080 LISTEN 안 됨 → background Popen 호출 ───────────────────────────
def test_on_starts_proxy_when_not_listening(tmp_layout, capsys):
    popen_calls = []

    def fake_popen(cmd, **kw):
        popen_calls.append(cmd)
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        return mock_proc

    with patch("agentbox._activate._is_listening", return_value=False), \
         patch("agentbox._activate.subprocess.Popen", side_effect=fake_popen), \
         patch("agentbox._activate._apply_iptables"):
        from agentbox._activate import on_command
        rc = on_command(project_root=tmp_layout)

    assert len(popen_calls) == 1
    assert "agentbox" in popen_calls[0]
    assert rc == 0


# ── T3: _off stdout에 unset 3줄 ──────────────────────────────────────────────
def test_off_stdout_unsets(tmp_layout, capsys):
    from agentbox._activate import off_command
    rc = off_command(project_root=tmp_layout)

    out = capsys.readouterr().out
    assert "unset HTTPS_PROXY" in out
    assert "unset NO_PROXY" in out
    assert "unset NODE_EXTRA_CA_CERTS" in out
    assert rc == 0


# ── T4: stderr는 user-facing, stdout은 export/unset만 ────────────────────────
def test_on_stdout_is_eval_safe(tmp_layout, capsys):
    """stdout must contain ONLY valid shell assignment statements (no [agentbox] messages)."""
    with patch("agentbox._activate._is_listening", return_value=False), \
         patch("agentbox._activate.subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        from agentbox._activate import on_command
        on_command(project_root=tmp_layout)

    captured = capsys.readouterr()
    for line in captured.out.splitlines():
        stripped = line.strip()
        if stripped:
            assert stripped.startswith("export ") or stripped.startswith("unset "), (
                f"stdout has non-eval-safe line: {stripped!r}"
            )
    # User-facing messages should be on stderr
    assert "[agentbox]" in captured.err


def test_off_stdout_is_eval_safe(tmp_layout, capsys):
    """stdout for _off must contain ONLY unset statements."""
    from agentbox._activate import off_command
    off_command(project_root=tmp_layout)

    captured = capsys.readouterr()
    for line in captured.out.splitlines():
        stripped = line.strip()
        if stripped:
            assert stripped.startswith("unset "), (
                f"stdout has non-eval-safe line: {stripped!r}"
            )


# ── C2: iptables integration ──────────────────────────────────────────────────
def test_on_calls_apply_redirect(tmp_layout, capsys):
    with patch("agentbox._activate._is_listening", return_value=True), \
         patch("agentbox._activate._apply_iptables") as mock_ipt:
        from agentbox._activate import on_command
        rc = on_command(project_root=tmp_layout, no_iptables=False)
    mock_ipt.assert_called_once()
    assert rc == 0


def test_on_no_iptables_skips_apply(tmp_layout, capsys):
    with patch("agentbox._activate._is_listening", return_value=True), \
         patch("agentbox._activate._apply_iptables") as mock_ipt:
        from agentbox._activate import on_command
        rc = on_command(project_root=tmp_layout, no_iptables=True)
    mock_ipt.assert_not_called()
    assert rc == 0


def test_off_calls_clear_redirect(tmp_layout, capsys):
    with patch("agentbox._activate._clear_iptables") as mock_ipt:
        from agentbox._activate import off_command
        rc = off_command(project_root=tmp_layout, no_iptables=False)
    mock_ipt.assert_called_once()
    assert rc == 0


def test_off_no_iptables_skips_clear(tmp_layout, capsys):
    with patch("agentbox._activate._clear_iptables") as mock_ipt:
        from agentbox._activate import off_command
        rc = off_command(project_root=tmp_layout, no_iptables=True)
    mock_ipt.assert_not_called()
    assert rc == 0


def test_apply_iptables_passes_host_and_port(tmp_layout):
    """Verify apply_redirect is called with api.anthropic.com and proxy port."""
    from agentbox._activate import _apply_iptables
    with patch("agentbox.proxy.iptables.apply_redirect") as mock_apply:
        mock_apply.return_value = None
        _apply_iptables(8080)
    mock_apply.assert_called_once()
    _, call_args, _ = mock_apply.mock_calls[0]
    port, hosts = call_args
    assert port == 8080
    assert "api.anthropic.com" in hosts
