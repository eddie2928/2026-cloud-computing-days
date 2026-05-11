"""agentbox init - encrypt project, upload to S3, verify EC2, print dashboard URL."""
import logging
import os
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from agentbox import last_init as _last_init
from agentbox.init_deps import DEPS, PYTHON_PACKAGES, check_dep, check_python_pkg, try_auto_install

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger("agentbox.init")


def _setup_file_logger() -> None:
    if logger.handlers:
        return
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = _PROJ_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / f"agentbox-init-{timestamp}.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def get_terraform_output(name: str) -> str | None:
    try:
        result = subprocess.run(
            ["terraform", "-chdir=infra", "output", "-raw", name],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.decode().strip()
    except Exception:
        pass
    return None


def _read_env_file(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _log(msg: str, level: str = "info") -> None:
    print(msg)
    getattr(logger, level)(msg)


def init(
    dir: str,
    project_id: str | None = None,
    skip_deps: bool = False,
    auto_yes: bool = False,
) -> int:
    _setup_file_logger()

    # Step 1 — Path validation
    src = Path(dir).expanduser().resolve()
    if not src.is_dir():
        _log(f"[agentbox] ERROR: '{dir}' is not a directory.", "error")
        return 2

    pid = project_id or src.name
    _log(f"[agentbox] PROJECT_ID={pid}")

    # Step 2 — Config validation
    sops_yaml = _PROJ_ROOT / ".sops.yaml"
    if not sops_yaml.exists():
        _log(
            "[agentbox] ERROR: .sops.yaml not found in project root.\n"
            "  Run: terraform -chdir=infra apply",
            "error",
        )
        return 3
    if "{region}" in sops_yaml.read_text():
        _log(
            "[agentbox] ERROR: .sops.yaml has placeholder KMS ARN.\n"
            "  Run: terraform -chdir=infra apply",
            "error",
        )
        return 3

    env_file = _PROJ_ROOT / ".env.endpoint"
    env_vars = _read_env_file(env_file)
    if "EC2_GRPC_HOST" not in env_vars:
        _log(
            f"[agentbox] ERROR: {env_file} missing or lacks EC2_GRPC_HOST.\n"
            "  Run: ./scripts/deploy.sh",
            "error",
        )
        return 3

    app_ip = env_vars["EC2_GRPC_HOST"]
    saas_url = get_terraform_output("saas_url") or f"http://{app_ip}:8000"

    # Step 3 — Dependency check
    if not skip_deps:
        failed = []
        for dep in DEPS:
            ok, _err = check_dep(dep)
            if not ok:
                failed.append(dep)

        if failed:
            names = ", ".join(d.name for d in failed)
            _log(f"[agentbox] 누락된 의존성: {names}", "warning")

            if not auto_yes:
                ans = input("자동 설치를 시도할까요? [y/N]: ").strip().lower()
                if ans != "y":
                    for dep in failed:
                        _log(f"  Install manually: {dep.name}")
                    return 4

            for dep in failed:
                _log(f"[agentbox] Installing {dep.name} ...")
                if not try_auto_install(dep):
                    _log(f"[agentbox] ERROR: Failed to install {dep.name}.", "error")
                    return 4

        for pkg in PYTHON_PACKAGES:
            ok = check_python_pkg(pkg)
            _log(f"[agentbox] python package {pkg}: {'OK' if ok else 'MISSING'}")

    # Step 4 — Encrypt + Upload
    env = os.environ.copy()
    project_name = os.environ.get("PROJECT_NAME", "agentbox")
    env["PROJECT_S3_BUCKET"] = f"{project_name}-encrypted-code"
    env["PROJECT_ID"] = pid

    script_path = str(_PROJ_ROOT / "scripts" / "encrypt_and_upload.sh")
    is_windows = platform.system() == "Windows"

    if is_windows:
        try:
            subprocess.run(["wsl", "echo", "ok"], capture_output=True, timeout=5, check=True)
            cmd = ["wsl", "bash", script_path, str(src)]
        except Exception:
            _log(
                "[agentbox] ERROR: WSL not found. Install WSL2 or run in WSL terminal:\n"
                "  bash scripts/encrypt_and_upload.sh <dir>",
                "error",
            )
            return 5
    else:
        cmd = ["bash", script_path, str(src)]

    _log(f"[agentbox] Encrypting and uploading {src} ...")
    result = subprocess.run(cmd, env=env, cwd=str(_PROJ_ROOT))
    if result.returncode != 0:
        _log(
            f"[agentbox] ERROR: Encryption/upload failed (exit {result.returncode}).",
            "error",
        )
        return 5

    # Step 5 — EC2 Connectivity
    _log(f"[agentbox] Checking EC2 connectivity ({app_ip}) ...")

    try:
        resp = requests.get(f"{saas_url}/healthz", timeout=5)
        if resp.status_code != 200:
            raise ValueError(f"HTTP {resp.status_code}")
    except Exception as exc:
        _log(
            f"[agentbox] ERROR: SaaS healthz failed: {exc}\n"
            "  Possible causes:\n"
            "  1. Security Group: check inbound port 8000 is open for your IP\n"
            "  2. SaaS service: systemctl status agentbox-saas on app-EC2\n"
            "  3. EIP reassigned: check app_public_ip in terraform output\n"
            "  4. Subnet egress: check route table for public subnet\n"
            "  5. DNS/firewall: try curl directly from inside VPC",
            "error",
        )
        return 6

    try:
        with socket.create_connection((app_ip, 50051), timeout=5):
            pass
    except OSError as exc:
        _log(
            f"[agentbox] ERROR: gRPC TCP connect failed: {exc}\n"
            "  Possible causes:\n"
            "  1. Security Group: check inbound port 50051 is open\n"
            "  2. gRPC service: systemctl status agentbox-grpc on app-EC2\n"
            "  3. mTLS: TCP test only, no SSL handshake attempted",
            "error",
        )
        return 7

    # Step 6 — Success
    s3_bucket = env["PROJECT_S3_BUCKET"]
    _last_init.write({
        "project_id": pid,
        "src_path": str(src),
        "s3_uri": f"s3://{s3_bucket}/encrypted_code/{pid}/",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "saas_url": saas_url,
    })
    _log(f"[agentbox] init OK. 대시보드: {saas_url}")
    return 0
