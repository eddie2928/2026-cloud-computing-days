#!/usr/bin/env python3
"""Verify/fix consistency between Terraform outputs and ~/.agentbox/ config.

Usage:
    python scripts/verify_consistency.py --check        # exit 0 if consistent, 1 if not
    python scripts/verify_consistency.py --fix          # prompt then apply fixes
    python scripts/verify_consistency.py --fix -y       # apply fixes without prompt
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_tf_output() -> dict | None:
    try:
        result = subprocess.run(
            ["terraform", "-chdir=infra", "output", "-json"],
            capture_output=True, timeout=30, cwd=str(_REPO_ROOT),
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def _get_tf_value(tf_output: dict, key: str) -> str | None:
    entry = tf_output.get(key, {})
    if isinstance(entry, dict):
        return entry.get("value")
    return None


def _read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _cert_expiry_ok(cert_path: Path, min_days: int = 7) -> bool:
    try:
        result = subprocess.run(
            ["openssl", "x509", "-checkend", str(min_days * 86400),
             "-noout", "-in", str(cert_path)],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def check(global_home: Path | None = None) -> list[dict]:
    """Run consistency checks. Returns list of diff items."""
    from agentbox.dotagentbox import _global_home
    home = global_home or _global_home()

    diffs = []

    tf = _run_tf_output()
    if tf is None:
        diffs.append({
            "key": "terraform_output",
            "status": "SKIP",
            "reason": "terraform output not available",
        })
        tf = {}

    # IP consistency
    tf_ip = _get_tf_value(tf, "app_public_ip")
    if tf_ip:
        env_vars = _read_env_file(home / "env")
        endpoint_vars = _read_env_file(home / "endpoint")
        for key, source, actual in [
            ("GRPC_HOST", "env", env_vars.get("GRPC_HOST")),
            ("EC2_GRPC_HOST", "endpoint", endpoint_vars.get("EC2_GRPC_HOST")),
        ]:
            if actual and actual != tf_ip:
                diffs.append({
                    "key": key,
                    "source": source,
                    "expected": tf_ip,
                    "actual": actual,
                    "status": "DIFF",
                    "file": str(home / source),
                })

    # KMS ARN consistency
    tf_kms = _get_tf_value(tf, "kms_key_arn")
    if tf_kms:
        sops = home / "sops.yaml"
        if sops.exists():
            content = sops.read_text(encoding="utf-8")
            if tf_kms not in content:
                diffs.append({
                    "key": "kms_key_arn",
                    "source": "sops.yaml",
                    "expected": tf_kms,
                    "actual": "(not found in sops.yaml)",
                    "status": "DIFF",
                    "file": str(sops),
                })

    # Cert existence + expiry
    certs_dir = home / "certs" / "grpc"
    for cert_name in ("agentbox-ca.crt", "endpoint.crt"):
        cert_path = certs_dir / cert_name
        if not cert_path.exists():
            diffs.append({
                "key": cert_name,
                "status": "MISSING",
                "file": str(cert_path),
            })
        elif not _cert_expiry_ok(cert_path):
            diffs.append({
                "key": cert_name,
                "status": "EXPIRED",
                "file": str(cert_path),
            })

    return diffs


def fix(diffs: list[dict], auto_yes: bool = False, global_home: Path | None = None) -> None:
    """Apply fixes for diff items."""
    from agentbox.dotagentbox import _global_home
    home = global_home or _global_home()

    tf = _run_tf_output() or {}
    tf_ip = _get_tf_value(tf, "app_public_ip")
    tf_kms = _get_tf_value(tf, "kms_key_arn")

    for diff in diffs:
        if diff["status"] == "SKIP":
            continue

        key = diff["key"]

        if not auto_yes:
            ans = input(f"Fix {key} ({diff['status']})? [y/N]: ").strip().lower()
            if ans != "y":
                print(f"Skipped {key}")
                continue

        if key == "GRPC_HOST" and tf_ip:
            _update_env_file(home / "env", "GRPC_HOST", tf_ip)
            print(f"Fixed {key} in env")
        elif key == "EC2_GRPC_HOST" and tf_ip:
            _update_env_file(home / "endpoint", "EC2_GRPC_HOST", tf_ip)
            print(f"Fixed {key} in endpoint")
        elif key == "kms_key_arn" and tf_kms:
            _update_sops_yaml(home / "sops.yaml", tf_kms)
            print(f"Fixed kms in sops.yaml")
        elif diff["status"] in ("MISSING", "EXPIRED"):
            print(f"Run: agentbox set  (to regenerate {key})")


def _update_env_file(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
    if not updated:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_sops_yaml(path: Path, kms_arn: str) -> None:
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    rules = data.get("creation_rules", [{}])
    if rules:
        rules[0]["kms"] = kms_arn
    data["creation_rules"] = rules
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check consistency (read-only)")
    group.add_argument("--fix", action="store_true", help="Fix inconsistencies")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all fixes")
    args = parser.parse_args()

    diffs = check()

    if args.check:
        if diffs:
            print(json.dumps(diffs, indent=2))
            return 1
        print("{}")
        return 0

    if args.fix:
        if not diffs:
            print("All consistent. Nothing to fix.")
            return 0
        print(json.dumps(diffs, indent=2))
        fix(diffs, auto_yes=args.yes)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
