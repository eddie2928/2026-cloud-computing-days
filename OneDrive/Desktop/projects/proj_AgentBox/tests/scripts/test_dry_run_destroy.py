"""Verify DRY_RUN=1 destroy.sh runs to completion without real AWS destroy."""
import os
import subprocess
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DESTROY_SH = os.path.join(REPO_ROOT, "scripts", "destroy.sh")


def _run_dry(script):
    env = os.environ.copy()
    # Strip fake creds injected by autouse fixture; let terraform use ~/.aws/credentials
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SECURITY_TOKEN", "AWS_SESSION_TOKEN"):
        env.pop(k, None)
    env["DRY_RUN"] = "1"
    env["TF_VAR_endpoint_cidr"] = "1.2.3.4/32"
    env["TF_VAR_admin_cidr"] = "1.2.3.4/32"
    env["TF_VAR_admin_token"] = "dummy-token"
    env["TF_VAR_alert_email"] = "test@example.com"
    env["TF_VAR_existing_kms_key_arn"] = ""
    result = subprocess.run(
        ["bash", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=REPO_ROOT,
    )
    return result


def test_destroy_bash_syntax():
    """destroy.sh should pass bash -n (syntax check)."""
    result = subprocess.run(["bash", "-n", DESTROY_SH], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error in destroy.sh:\n{result.stderr}"


def test_dry_run_destroy_exits_zero():
    """DRY_RUN=1 destroy.sh should exit 0."""
    result = _run_dry(DESTROY_SH)
    assert result.returncode == 0, (
        f"DRY_RUN destroy.sh failed (exit {result.returncode})\n"
        f"stdout: {result.stdout[-2000:]}\n"
        f"stderr: {result.stderr[-1000:]}"
    )


def test_dry_run_destroy_outputs_plan():
    """DRY_RUN=1 destroy.sh stdout should contain 'Plan:' or 'DRY_RUN'."""
    result = _run_dry(DESTROY_SH)
    assert "Plan:" in result.stdout or "DRY_RUN" in result.stdout, (
        f"Expected 'Plan:' or 'DRY_RUN' in stdout:\n{result.stdout[-3000:]}"
    )
