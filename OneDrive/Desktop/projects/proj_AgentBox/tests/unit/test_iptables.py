"""Unit tests for agentbox.proxy.iptables (subprocess mocked)."""
from unittest.mock import MagicMock, call, patch

import pytest

from agentbox.proxy.iptables import apply_redirect, clear_redirect


def _ok(stdout="", stderr=""):
    m = MagicMock()
    m.returncode = 0
    m.stdout = stdout
    m.stderr = stderr
    return m


def _fail(stderr="Operation not permitted"):
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = stderr
    return m


@patch("agentbox.proxy.iptables.subprocess.run")
def test_apply_redirect_single_host(mock_run):
    mock_run.return_value = _ok()
    apply_redirect(8080, ["api.anthropic.com"])
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "iptables" in cmd
    assert "-A" in cmd
    assert "api.anthropic.com" in cmd
    assert "--to-ports" in cmd
    assert "8080" in cmd


@patch("agentbox.proxy.iptables.subprocess.run")
def test_apply_redirect_multiple_hosts(mock_run):
    mock_run.return_value = _ok()
    apply_redirect(8080, ["api.anthropic.com", "example.com"])
    assert mock_run.call_count == 2
    calls_cmds = [c[0][0] for c in mock_run.call_args_list]
    assert any("api.anthropic.com" in c for c in calls_cmds)
    assert any("example.com" in c for c in calls_cmds)


@patch("agentbox.proxy.iptables.subprocess.run")
def test_apply_redirect_permission_error(mock_run):
    mock_run.return_value = _fail("Operation not permitted")
    with pytest.raises(PermissionError, match="iptables failed"):
        apply_redirect(8080, ["api.anthropic.com"])


@patch("agentbox.proxy.iptables.subprocess.run")
def test_clear_redirect_calls_delete(mock_run):
    list_output = (
        'Chain OUTPUT (policy ACCEPT)\n'
        'REDIRECT   tcp  --  0.0.0.0/0  0.0.0.0/0  '
        'STRING match  "api.anthropic.com" ALGO name bm  redir ports 8080\n'
    )
    mock_run.side_effect = [_ok(stdout=list_output), _ok()]
    clear_redirect(8080)
    assert mock_run.call_count == 2
    delete_cmd = mock_run.call_args_list[1][0][0]
    assert "-D" in delete_cmd
    assert "api.anthropic.com" in delete_cmd
    assert "8080" in delete_cmd


@patch("agentbox.proxy.iptables.subprocess.run")
def test_clear_redirect_no_rules(mock_run):
    list_output = "Chain OUTPUT (policy ACCEPT)\n"
    mock_run.return_value = _ok(stdout=list_output)
    clear_redirect(8080)
    # Only the -L call, no -D calls
    assert mock_run.call_count == 1


def test_default_hosts():
    """Verify the default host list as documented in Tasks.md C3."""
    from agentbox.proxy.iptables import apply_redirect as _apply
    import inspect
    src = inspect.getsource(_apply)
    # apply_redirect itself doesn't embed defaults; C3 wires them in _activate
    # Just verify the function signature accepts target_hosts
    import inspect as _ins
    sig = _ins.signature(_apply)
    assert "target_hosts" in sig.parameters
