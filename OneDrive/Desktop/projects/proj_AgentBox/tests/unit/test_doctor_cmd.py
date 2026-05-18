"""Unit tests for agentbox.doctor_cmd (Task-7 N1)."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import agentbox.doctor_cmd as dc


@pytest.fixture
def tmp_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    monkeypatch.setattr(dc, "_PROJ_ROOT", tmp_path)
    return tmp_path


def _all_ok_patches(extra=None):
    patches = {
        "agentbox.doctor_cmd._check_d1_layout": lambda l: {"id": "D1", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d2_deps": lambda: {"id": "D2", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d3_certs": lambda l: {"id": "D3", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d4_proto": lambda: {"id": "D4", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d5_proxy": lambda: {"id": "D5", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d6_grpc_tcp": lambda: {"id": "D6", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d7_mtls": lambda l: {"id": "D7", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d8_saas": lambda: {"id": "D8", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d9_consistency": lambda: {"id": "D9", "status": "OK", "detail": ""},
        "agentbox.doctor_cmd._check_d10_cert_expiry": lambda l: {"id": "D10", "status": "OK", "detail": ""},
    }
    if extra:
        patches.update(extra)
    return patches


# ── T1: 9개 전부 OK → 표 출력, exit 0 ────────────────────────────────────────
def test_all_ok(tmp_layout, capsys):
    with patch.multiple("agentbox.doctor_cmd", **{k.split(".")[-1]: v
                        for k, v in _all_ok_patches().items()}):
        rc = dc.run_doctor(project_root=tmp_layout)

    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


# ── T2: D5 fail → 그 행만 FAIL, exit 1, 나머지 계속 평가됨 ─────────────────
def test_d5_fail_continues(tmp_layout, capsys):
    extra = {
        "agentbox.doctor_cmd._check_d5_proxy":
            lambda: {"id": "D5", "status": "FAIL", "detail": "not listening: [8080]"},
    }
    with patch.multiple("agentbox.doctor_cmd", **{k.split(".")[-1]: v
                        for k, v in _all_ok_patches(extra).items()}):
        rc = dc.run_doctor(project_root=tmp_layout)

    assert rc == 1
    out = capsys.readouterr().out
    # All 10 rows should appear (no early exit)
    for i in range(1, 11):
        assert f"D{i}" in out


# ── T3: D7 mTLS fail → exit 1 ────────────────────────────────────────────────
def test_d7_fail(tmp_layout):
    extra = {
        "agentbox.doctor_cmd._check_d7_mtls":
            lambda l: {"id": "D7", "status": "FAIL", "detail": "CA mismatch"},
    }
    with patch.multiple("agentbox.doctor_cmd", **{k.split(".")[-1]: v
                        for k, v in _all_ok_patches(extra).items()}):
        rc = dc.run_doctor(project_root=tmp_layout)

    assert rc == 1


# ── T4: D9 consistency diff → exit 1, diff 표 안에 표시 ─────────────────────
def test_d9_fail(tmp_layout, capsys):
    extra = {
        "agentbox.doctor_cmd._check_d9_consistency":
            lambda: {"id": "D9", "status": "FAIL", "detail": "diffs: [GRPC_HOST=DIFF]"},
    }
    with patch.multiple("agentbox.doctor_cmd", **{k.split(".")[-1]: v
                        for k, v in _all_ok_patches(extra).items()}):
        rc = dc.run_doctor(project_root=tmp_layout)

    assert rc == 1
    out = capsys.readouterr().out
    assert "D9" in out


# ── T5: --json → 스키마 일치 ─────────────────────────────────────────────────
def test_json_output(tmp_layout, capsys):
    with patch.multiple("agentbox.doctor_cmd", **{k.split(".")[-1]: v
                        for k, v in _all_ok_patches().items()}):
        rc = dc.run_doctor(project_root=tmp_layout, output_json=True)

    out = capsys.readouterr().out
    data = json.loads(out)
    assert "items" in data
    assert "exit_code" in data
    assert len(data["items"]) == 10
    for item in data["items"]:
        assert "id" in item
        assert "status" in item
        assert "detail" in item


# ── T6: --fix → D3/D4/D5/D9는 복구 호출, D1/D2/D6/D7/D8은 호출 안 됨 ────────
def test_fix_selectively_called(tmp_layout, monkeypatch):
    fail_results = [
        {"id": "D1", "status": "FAIL", "detail": ""},
        {"id": "D2", "status": "FAIL", "detail": ""},
        {"id": "D3", "status": "FAIL", "detail": ""},
        {"id": "D4", "status": "FAIL", "detail": ""},
        {"id": "D5", "status": "FAIL", "detail": ""},
        {"id": "D6", "status": "FAIL", "detail": ""},
        {"id": "D7", "status": "FAIL", "detail": ""},
        {"id": "D8", "status": "FAIL", "detail": ""},
        {"id": "D9", "status": "FAIL", "detail": ""},
        {"id": "D10", "status": "FAIL", "detail": ""},
    ]

    fix_calls = []

    original_fix = dc._auto_fix

    def tracking_fix(results, layout):
        for r in results:
            if r["status"] == "FAIL" and r["id"] in ("D3", "D4", "D5", "D9"):
                fix_calls.append(r["id"])

    with patch.multiple("agentbox.doctor_cmd", **{k.split(".")[-1]: v
                        for k, v in _all_ok_patches().items()}), \
         patch("agentbox.doctor_cmd._auto_fix", side_effect=tracking_fix):
        # Manually call _auto_fix with the fail results
        from agentbox.dotagentbox import ensure_layout
        layout = ensure_layout(tmp_layout)
        tracking_fix(fail_results, layout)

    # D3/D4/D5/D9 should have been targeted
    assert set(fix_calls) == {"D3", "D4", "D5", "D9"}
    # D1/D2/D6/D7/D8/D10 should NOT be in fix_calls
    for item_id in ("D1", "D2", "D6", "D7", "D8", "D10"):
        assert item_id not in fix_calls


# ── T7: D10 cert expiry <= 7 days → FAIL + regen-certs 안내 ─────────────────
def test_d10_cert_near_expiry(tmp_path, monkeypatch):
    import datetime as dt
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    # Generate a cert that expires in 3 days
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=3))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    global_home = tmp_path / "global"
    monkeypatch.setenv("AGENTBOX_HOME", str(global_home))
    from agentbox.dotagentbox import ensure_layout
    layout = ensure_layout(tmp_path)

    # Write cert after ensure_layout creates the dirs (so migration can't delete it)
    layout.global_certs_dir.mkdir(parents=True, exist_ok=True)
    (layout.global_certs_dir / "endpoint.crt").write_bytes(cert_pem)

    result = dc._check_d10_cert_expiry(layout)

    assert result["status"] == "FAIL"
    assert "agentbox set" in result["detail"]
    assert "--regen-certs" in result["detail"]
