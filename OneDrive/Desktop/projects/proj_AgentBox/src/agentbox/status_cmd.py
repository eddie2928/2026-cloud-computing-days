"""agentbox status — print current AgentBox runtime state."""
import json
import logging
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import requests

from agentbox import last_init
from agentbox.init_cmd import get_terraform_output
from agentbox.init_deps import DEPS, PYTHON_PACKAGES, check_dep, check_python_pkg

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger("agentbox.status")


def _get_saas_url() -> str | None:
    meta = last_init.read()
    if meta and meta.get("saas_url"):
        return meta["saas_url"]

    url = get_terraform_output("saas_url")
    if url:
        return url

    env_file = _PROJ_ROOT / ".env.endpoint"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("EC2_GRPC_HOST="):
                ip = line.split("=", 1)[1].strip()
                if ip:
                    return f"http://{ip}:8000"
    return None


def _get_deps_status() -> dict[str, bool]:
    result: dict[str, bool] = {}
    for dep in DEPS:
        ok, _ = check_dep(dep)
        result[dep.name] = ok
    for pkg in PYTHON_PACKAGES:
        result[pkg] = check_python_pkg(pkg)
    return result


def _get_proxy_state() -> dict:
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    listening = False
    try:
        with socket.create_connection(("127.0.0.1", 8080), timeout=0.5):
            listening = True
    except OSError:
        pass
    return {"https_proxy_env": https_proxy, "listening_8080": listening}


def _get_last_init() -> dict | None:
    return last_init.read()


def _get_connectivity(saas_url: str | None, grpc_host: str | None) -> dict:
    result: dict = {}

    if saas_url:
        try:
            resp = requests.get(saas_url + "/healthz", timeout=3)
            result["saas_healthz"] = resp.status_code
        except Exception as exc:
            result["saas_healthz"] = f"ERROR: {exc}"
    else:
        result["saas_healthz"] = "URL unknown"

    if grpc_host:
        try:
            with socket.create_connection((grpc_host, 50051), timeout=3):
                pass
            result["grpc_tcp"] = True
        except Exception as exc:
            result["grpc_tcp"] = f"ERROR: {exc}"
    else:
        result["grpc_tcp"] = "host unknown"

    return result


def _extract_grpc_host(saas_url: str | None) -> str | None:
    if not saas_url:
        return None
    try:
        return urlparse(saas_url).hostname
    except Exception:
        return None


def run_status(args) -> int:
    saas_url = _get_saas_url()
    deps = _get_deps_status()
    proxy = _get_proxy_state()
    last = _get_last_init()
    grpc_host = _extract_grpc_host(saas_url)
    connectivity = _get_connectivity(saas_url, grpc_host)

    if getattr(args, "json", False):
        output = {
            "saas_url": saas_url,
            "dependencies": deps,
            "proxy": proxy,
            "last_init": last,
            "connectivity": connectivity,
            "meta": {"author": "JeonMyeonghwan"},
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    deps_str = " | ".join(f"{k} {'OK' if v else 'MISSING'}" for k, v in deps.items())

    proxy_on = bool(proxy["https_proxy_env"]) and proxy["listening_8080"]
    if proxy_on:
        proxy_str = f"ON  (HTTPS_PROXY={proxy['https_proxy_env']}, :8080 LISTEN)"
    elif proxy["https_proxy_env"]:
        proxy_str = f"ENV set ({proxy['https_proxy_env']}) but :8080 NOT listening"
    else:
        proxy_str = "OFF"

    if last:
        pid = last.get("project_id", "?")
        uploaded = last.get("uploaded_at", "?")
        s3 = last.get("s3_uri", "?")
        last_str = f"project_id={pid} ({uploaded})\n{'':26}s3={s3}"
    else:
        last_str = "No previous init"

    saas_h = connectivity.get("saas_healthz", "?")
    grpc_t = connectivity.get("grpc_tcp", "?")
    conn_str = f"/healthz={saas_h} | gRPC :50051={grpc_t}"

    print("AgentBox Status")
    print("=" * 50)
    print(f"1. SaaS Dashboard URL : {saas_url or 'Unknown'}")
    print(f"2. Dependencies        : {deps_str}")
    print(f"3. Proxy state         : {proxy_str}")
    print(f"4. Last init           : {last_str}")
    print(f"5. EC2 connectivity    : {conn_str}")
    print("-" * 50)
    print("Made by JeonMyeonghwan")

    return 0
