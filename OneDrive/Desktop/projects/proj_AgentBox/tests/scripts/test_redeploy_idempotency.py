"""redeploy_idempotency.sh dry-run 출력 검증."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJ_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJ_ROOT / "scripts" / "redeploy_idempotency.sh"

_HAS_TERRAFORM = shutil.which("terraform") is not None
_HAS_AWS_CREDS = subprocess.run(
    ["aws", "sts", "get-caller-identity", "--region", "us-east-1"],
    capture_output=True, timeout=10
).returncode == 0 if shutil.which("aws") else False


_TF_AUTH_ERRORS = (
    "InvalidClientTokenId", "NoCredentialProviders",
    "ExpiredToken", "AccessDenied", "error configuring Terraform AWS",
)


@pytest.mark.skipif(
    not SCRIPT.exists(),
    reason="redeploy_idempotency.sh missing"
)
@pytest.mark.skipif(
    not (_HAS_TERRAFORM and _HAS_AWS_CREDS),
    reason="terraform or valid AWS credentials not available"
)
def test_dry_run_executes_destroy_then_deploy(tmp_path):
    env = os.environ.copy()
    env["DRY_RUN"] = "1"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        cwd=str(PROJ_ROOT),
    )
    out = result.stdout + result.stderr
    # Terraform initializes the AWS provider even for state/plan commands; if the
    # bash subprocess resolves credentials differently (e.g. SSO vs env vars), skip.
    if any(e in out for e in _TF_AUTH_ERRORS):
        pytest.skip(f"terraform AWS auth unavailable in bash subprocess: {out[-300:]}")
    assert "[0/5]" in out, f"사전 점검 누락: {out[-500:]}"
    assert "[1/5]" in out and "destroy.sh" in out
    assert "[2/5]" in out and "deploy.sh" in out
    assert "DRY_RUN 종료" in out
    assert result.returncode == 0, out[-500:]


@pytest.mark.skipif(not SCRIPT.exists(), reason="redeploy_idempotency.sh missing")
def test_script_syntax_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
