"""Verify DRY_RUN=1 deploy.sh runs to completion without real AWS apply."""
import os
import subprocess
import sys
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DEPLOY_SH = os.path.join(REPO_ROOT, "scripts", "deploy.sh")


def _run_dry(script, extra_env=None):
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
    env["TFVARS"] = "../tests/terraform/test.tfvars"
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["bash", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=REPO_ROOT,
    )
    return result


def test_deploy_bash_syntax():
    """deploy.sh should pass bash -n (syntax check)."""
    result = subprocess.run(["bash", "-n", DEPLOY_SH], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error in deploy.sh:\n{result.stderr}"


def test_dry_run_deploy_exits_zero():
    """DRY_RUN=1 deploy.sh should exit 0."""
    result = _run_dry(DEPLOY_SH)
    assert result.returncode == 0, (
        f"DRY_RUN deploy.sh failed (exit {result.returncode})\n"
        f"stdout: {result.stdout[-2000:]}\n"
        f"stderr: {result.stderr[-1000:]}"
    )


def test_dry_run_deploy_outputs_plan():
    """DRY_RUN=1 deploy.sh stdout should contain 'Plan:' or 'DRY_RUN'."""
    result = _run_dry(DEPLOY_SH)
    assert "Plan:" in result.stdout or "DRY_RUN" in result.stdout, (
        f"Expected 'Plan:' or 'DRY_RUN' in stdout:\n{result.stdout[-3000:]}"
    )


def test_dry_run_deploy_skips_apply():
    """DRY_RUN=1 deploy.sh should NOT call 'terraform apply'."""
    result = _run_dry(DEPLOY_SH)
    assert "terraform apply" not in result.stdout or "생략" in result.stdout, (
        "terraform apply should be skipped in DRY_RUN mode"
    )
