"""Unit tests for agentbox.ca_install (Task-7 E1)."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agentbox.ca_install import install_to_trust_store


@pytest.fixture
def ca_cert(tmp_path):
    cert = tmp_path / "agentbox-ca.crt"
    cert.write_bytes(b"FAKE CERT")
    return cert


# ── T1: trust store에 이미 있음(openssl verify=0) → noop (actually just runs cp) ─
def test_install_with_sudo_ok(ca_cert):
    with patch("agentbox.ca_install.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        rc = install_to_trust_store(ca_cert)

    assert rc == 0
    # sudo cp and update-ca-certificates called
    calls = [str(c) for c in mock_run.call_args_list]
    assert any("cp" in c for c in calls)


# ── T2: sudo 불가 → hint stdout만, exit 0 (warning) ─────────────────────────
def test_install_no_sudo_prints_hint(ca_cert, capsys):
    def fake_run(cmd, *a, **kw):
        if cmd[:2] == ["sudo", "-n"]:
            return MagicMock(returncode=1)
        return MagicMock(returncode=0)

    with patch("agentbox.ca_install.subprocess.run", side_effect=fake_run):
        rc = install_to_trust_store(ca_cert)

    assert rc == 0
    captured = capsys.readouterr()
    assert "sudo" in captured.out or "sudo" in captured.err


# ── T3: CA cert 없음 → return 1 ──────────────────────────────────────────────
def test_install_missing_cert(tmp_path):
    missing = tmp_path / "no.crt"
    rc = install_to_trust_store(missing)
    assert rc == 1
