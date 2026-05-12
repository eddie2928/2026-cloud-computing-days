"""Unit tests for scripts/verify_consistency.py (Task-7 I1+I2)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import verify_consistency as vc


@pytest.fixture
def global_home(tmp_path, monkeypatch):
    home = tmp_path / "global"
    home.mkdir()
    (home / "certs" / "grpc").mkdir(parents=True)
    monkeypatch.setenv("AGENTBOX_HOME", str(home))
    return home


def _make_valid_certs(home: Path):
    """Create dummy cert files that appear valid (openssl not called)."""
    (home / "certs" / "grpc" / "agentbox-ca.crt").write_bytes(b"FAKE")
    (home / "certs" / "grpc" / "endpoint.crt").write_bytes(b"FAKE")


def _fake_tf_output(ip="1.2.3.4", kms="arn:aws:kms:us-east-1:123:key/abc"):
    return {"app_public_ip": {"value": ip}, "kms_key_arn": {"value": kms}}


# ── T1: tf output 일치 + certs OK → --check exit 0 ────────────────────────────
def test_check_consistent(global_home):
    (global_home / "env").write_text("GRPC_HOST=1.2.3.4\n")
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=1.2.3.4\n")
    (global_home / "sops.yaml").write_text(
        "creation_rules:\n  - kms: arn:aws:kms:us-east-1:123:key/abc\n"
    )
    _make_valid_certs(global_home)

    with patch("verify_consistency._run_tf_output", return_value=_fake_tf_output()), \
         patch("verify_consistency._cert_expiry_ok", return_value=True):
        diffs = vc.check(global_home=global_home)

    assert diffs == []


# ── T2: IP 다름 → --check exit 1 + JSON diff ─────────────────────────────────
def test_check_ip_mismatch(global_home):
    (global_home / "env").write_text("GRPC_HOST=9.9.9.9\n")  # differs from tf
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=9.9.9.9\n")
    (global_home / "sops.yaml").write_text(
        "creation_rules:\n  - kms: arn:aws:kms:us-east-1:123:key/abc\n"
    )
    _make_valid_certs(global_home)

    with patch("verify_consistency._run_tf_output", return_value=_fake_tf_output(ip="1.2.3.4")), \
         patch("verify_consistency._cert_expiry_ok", return_value=True):
        diffs = vc.check(global_home=global_home)

    assert any(d["key"] == "GRPC_HOST" and d["status"] == "DIFF" for d in diffs)


# ── T3: --fix -y → 파일 덮어써짐 ─────────────────────────────────────────────
def test_fix_auto_updates_ip(global_home):
    (global_home / "env").write_text("GRPC_HOST=9.9.9.9\n")
    diffs = [{"key": "GRPC_HOST", "status": "DIFF", "source": "env",
               "expected": "1.2.3.4", "actual": "9.9.9.9"}]

    with patch("verify_consistency._run_tf_output", return_value=_fake_tf_output()):
        vc.fix(diffs, auto_yes=True, global_home=global_home)

    env_vars = vc._read_env_file(global_home / "env")
    assert env_vars["GRPC_HOST"] == "1.2.3.4"


# ── T4: KMS ARN diff → sops.yaml 갱신 ────────────────────────────────────────
def test_fix_kms_arn(global_home):
    (global_home / "sops.yaml").write_text(
        "creation_rules:\n  - kms: arn:aws:kms:us-east-1:OLD:key/old\n"
    )
    diffs = [{"key": "kms_key_arn", "status": "DIFF",
               "expected": "arn:aws:kms:us-east-1:NEW:key/new",
               "actual": "arn:aws:kms:us-east-1:OLD:key/old"}]

    with patch("verify_consistency._run_tf_output",
               return_value=_fake_tf_output(kms="arn:aws:kms:us-east-1:NEW:key/new")):
        vc.fix(diffs, auto_yes=True, global_home=global_home)

    content = (global_home / "sops.yaml").read_text()
    assert "NEW" in content


# ── T5: cert 만료 → diff에 cert 항목 ─────────────────────────────────────────
def test_expired_cert_in_diff(global_home):
    _make_valid_certs(global_home)
    (global_home / "env").write_text("GRPC_HOST=1.2.3.4\n")
    (global_home / "endpoint").write_text("EC2_GRPC_HOST=1.2.3.4\n")
    (global_home / "sops.yaml").write_text(
        "creation_rules:\n  - kms: arn:aws:kms:us-east-1:123:key/abc\n"
    )

    # agentbox-ca.crt = expired (returns False), endpoint.crt = OK (returns True)
    def fake_expiry(path, **kw):
        return "agentbox-ca.crt" not in str(path)

    with patch("verify_consistency._run_tf_output", return_value=_fake_tf_output()), \
         patch("verify_consistency._cert_expiry_ok", side_effect=fake_expiry):
        diffs = vc.check(global_home=global_home)

    assert any(d["key"] == "agentbox-ca.crt" and d["status"] == "EXPIRED" for d in diffs)
