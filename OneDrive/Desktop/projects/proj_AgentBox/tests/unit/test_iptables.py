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
    """api.anthropic.com is the only default host when redirect_hosts file is absent."""
    from agentbox.proxy.iptables import load_redirect_hosts, _HOSTS_FILE
    with patch.object(_HOSTS_FILE.__class__, "exists", return_value=False):
        hosts = load_redirect_hosts()
    assert hosts == ["api.anthropic.com"]


def test_default_hosts_extended_from_file(tmp_path):
    """Additional hosts from ~/.agentbox/redirect_hosts are appended."""
    from agentbox.proxy.iptables import load_redirect_hosts, _HOSTS_FILE
    hosts_file = tmp_path / "redirect_hosts"
    hosts_file.write_text("example.com\nfoo.bar\n")
    import agentbox.proxy.iptables as _mod
    orig = _mod._HOSTS_FILE
    _mod._HOSTS_FILE = hosts_file
    try:
        hosts = load_redirect_hosts()
    finally:
        _mod._HOSTS_FILE = orig
    assert "api.anthropic.com" in hosts
    assert "example.com" in hosts
    assert "foo.bar" in hosts
