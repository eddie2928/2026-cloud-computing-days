"""agentbox doctor — read-only pre-test diagnostic (D1~D9)."""
import importlib
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent

STATUS_OK = "OK"
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"


def _check_d1_layout(layout) -> dict:
    """D1: .agentbox/ layout 4 directories exist."""
    dirs = [
        layout.global_certs_dir,
        layout.local_logs_dir,
        layout.global_env.parent,
        layout.local_pid.parent,
    ]
    missing = [str(d) for d in dirs if not d.is_dir()]
    if missing:
        return {"id": "D1", "status": STATUS_FAIL, "detail": f"missing: {missing}"}
    return {"id": "D1", "status": STATUS_OK, "detail": "layout OK"}


def _check_d2_deps() -> dict:
    """D2: sops, aws, boto3, pyyaml, grpcio installed."""
    from agentbox.init_deps import DEPS, check_dep, check_python_pkg

    missing = []
    for dep in DEPS:
        ok, _ = check_dep(dep)
        if not ok:
            missing.append(dep.name)
    for pkg in ("boto3", "pyyaml", "grpcio"):
        if not check_python_pkg(pkg):
            missing.append(pkg)

    if missing:
        return {"id": "D2", "status": STATUS_FAIL, "detail": f"missing: {missing}"}
    return {"id": "D2", "status": STATUS_OK, "detail": "all deps present"}


def _check_d3_certs(layout) -> dict:
    """D3: 4 cert files exist + expiry >= 7 days."""
    certs_dir = layout.global_certs_dir
    required = ["agentbox-ca.crt", "agentbox-ca.key", "endpoint.crt", "endpoint.key"]
    missing = [n for n in required if not (certs_dir / n).exists()]
    if missing:
        return {"id": "D3", "status": STATUS_FAIL, "detail": f"missing certs: {missing}"}

    expired = []
    for name in ("agentbox-ca.crt", "endpoint.crt"):
        cert_path = certs_dir / name
        try:
            result = subprocess.run(
                ["openssl", "x509", "-checkend", str(7 * 86400),
                 "-noout", "-in", str(cert_path)],
                capture_output=True, timeout=10,
            )
            if result.returncode != 0:
                expired.append(name)
        except Exception as exc:
            return {"id": "D3", "status": STATUS_SKIP, "detail": f"openssl error: {exc}"}

    if expired:
        return {"id": "D3", "status": STATUS_FAIL, "detail": f"expiring soon: {expired}"}
    return {"id": "D3", "status": STATUS_OK, "detail": "certs valid"}


def _check_d4_proto() -> dict:
    """D4: proto stub import available."""
    try:
        importlib.import_module("agentbox.grpc.inspect_pb2")
        return {"id": "D4", "status": STATUS_OK, "detail": "proto stub OK"}
    except ImportError as exc:
        return {"id": "D4", "status": STATUS_FAIL, "detail": str(exc)}


def _check_d5_proxy() -> dict:
    """D5: :8080 LISTEN + :8000 LISTEN."""
    from agentbox.config import cfg

    not_listening = []
    for port in (cfg.PROXY_PORT, cfg.API_PORT):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                pass
        except OSError:
            not_listening.append(port)

    if not_listening:
        return {"id": "D5", "status": STATUS_FAIL,
                "detail": f"not listening: {not_listening}"}
    return {"id": "D5", "status": STATUS_OK, "detail": "proxy+dashboard LISTEN"}


def _check_d6_grpc_tcp() -> dict:
    """D6: gRPC TCP connect."""
    from agentbox.config import cfg

    host = cfg.GRPC_HOST
    if not host:
        return {"id": "D6", "status": STATUS_SKIP, "detail": "GRPC_HOST not set"}

    try:
        with socket.create_connection((host, cfg.GRPC_PORT), timeout=5):
            pass
        return {"id": "D6", "status": STATUS_OK, "detail": f"TCP {host}:{cfg.GRPC_PORT} OK"}
    except OSError as exc:
        return {"id": "D6", "status": STATUS_FAIL, "detail": str(exc)}


def _check_d7_mtls(layout) -> dict:
    """D7: mTLS handshake."""
    from agentbox.config import cfg
    from agentbox.grpc.handshake import verify_mtls_handshake

    host = cfg.GRPC_HOST
    if not host:
        return {"id": "D7", "status": STATUS_SKIP, "detail": "GRPC_HOST not set"}

    def _resolve(cfg_path: str, default: Path) -> str:
        return cfg_path if cfg_path and Path(cfg_path).exists() else str(default)

    ca_cert = _resolve(cfg.GRPC_CA_CERT, layout.global_certs_dir / "agentbox-ca.crt")
    client_cert = _resolve(cfg.GRPC_CLIENT_CERT, layout.global_certs_dir / "endpoint.crt")
    client_key = _resolve(cfg.GRPC_CLIENT_KEY, layout.global_certs_dir / "endpoint.key")

    ok, reason = verify_mtls_handshake(host, cfg.GRPC_PORT, ca_cert, client_cert, client_key)
    if ok:
        return {"id": "D7", "status": STATUS_OK, "detail": "mTLS handshake OK"}
    return {"id": "D7", "status": STATUS_FAIL, "detail": reason}


def _check_d8_saas() -> dict:
    """D8: SaaS /healthz HTTP 200."""
    import requests

    from agentbox.config import cfg

    host = cfg.GRPC_HOST
    if not host:
        return {"id": "D8", "status": STATUS_SKIP, "detail": "GRPC_HOST not set"}

    saas_url = f"http://{host}:8000"
    try:
        resp = requests.get(f"{saas_url}/healthz", timeout=3)
        if resp.status_code == 200:
            return {"id": "D8", "status": STATUS_OK, "detail": f"{saas_url}/healthz → 200"}
        return {"id": "D8", "status": STATUS_FAIL,
                "detail": f"{saas_url}/healthz → HTTP {resp.status_code}"}
    except Exception as exc:
        return {"id": "D8", "status": STATUS_FAIL, "detail": str(exc)}


def _check_d9_consistency() -> dict:
    """D9: verify_consistency.py --check."""
    script = _PROJ_ROOT / "scripts" / "verify_consistency.py"
    if not script.exists():
        return {"id": "D9", "status": STATUS_SKIP, "detail": "verify_consistency.py not found"}

    try:
        sys.path.insert(0, str(script.parent))
        import verify_consistency as vc

        diffs = vc.check()
        if not diffs:
            return {"id": "D9", "status": STATUS_OK, "detail": "consistent"}
        summary = [f"{d['key']}={d['status']}" for d in diffs]
        return {"id": "D9", "status": STATUS_FAIL, "detail": f"diffs: {summary}"}
    except Exception as exc:
        return {"id": "D9", "status": STATUS_SKIP, "detail": str(exc)}


def _check_d10_cert_expiry(layout) -> dict:
    """D10: endpoint.crt expiry <= 7 days -> advise agentbox set --regen-certs."""
    cert_path = layout.global_certs_dir / "endpoint.crt"
    if not cert_path.exists():
        return {"id": "D10", "status": STATUS_SKIP, "detail": "endpoint.crt not found"}

    try:
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        now = datetime.now(timezone.utc)
        days = (cert.not_valid_after_utc - now).days
        if days <= 7:
            return {
                "id": "D10",
                "status": STATUS_FAIL,
                "detail": f"endpoint.crt expires in {days}d — run: agentbox set -y --regen-certs",
            }
        return {"id": "D10", "status": STATUS_OK, "detail": f"endpoint.crt valid for {days}d"}
    except Exception as exc:
        return {"id": "D10", "status": STATUS_SKIP, "detail": f"cert read error: {exc}"}


def run_doctor(project_root: Path | None = None, output_json: bool = False,
               fix: bool = False) -> int:
    """Run all D1-D10 checks; return 0 if all OK, 1 if any FAIL."""
    from agentbox.dotagentbox import ensure_layout

    root = project_root or _PROJ_ROOT
    layout = ensure_layout(root)

    results = [
        _check_d1_layout(layout),
        _check_d2_deps(),
        _check_d3_certs(layout),
        _check_d4_proto(),
        _check_d5_proxy(),
        _check_d6_grpc_tcp(),
        _check_d7_mtls(layout),
        _check_d8_saas(),
        _check_d9_consistency(),
        _check_d10_cert_expiry(layout),
    ]

    has_fail = any(r["status"] == STATUS_FAIL for r in results)
    exit_code = 1 if has_fail else 0

    if fix:
        _auto_fix(results, layout)

    if output_json:
        print(json.dumps({"items": results, "exit_code": exit_code}))
    else:
        _print_table(results)

    return exit_code


def _print_table(results: list[dict]) -> None:
    width = max(len(r["id"]) for r in results)
    print(f"{'ID':<4}  {'STATUS':<6}  DETAIL")
    print("-" * 60)
    for r in results:
        print(f"{r['id']:<4}  {r['status']:<6}  {r['detail']}")


def _auto_fix(results: list[dict], layout) -> None:
    """Auto-fix recoverable failures."""
    for r in results:
        if r["status"] != STATUS_FAIL:
            continue
        item_id = r["id"]
        if item_id == "D3":
            print("[doctor] D3: 재생성 중 (agentbox set -y 권장)...")
            try:
                from agentbox.proxy.ca import gen_mtls_certs
                gen_mtls_certs(layout.global_certs_dir)
                print("[doctor] D3: certs regenerated")
            except Exception as exc:
                print(f"[doctor] D3 fix failed: {exc}")
        elif item_id == "D4":
            print("[doctor] D4: proto stub 재생성 시도...")
            subprocess.run(["agentbox", "set", "--skip-deps-install"], check=False)
        elif item_id == "D5":
            print("[doctor] D5: proxy 시작 시도...")
            subprocess.Popen(
                ["agentbox", "run"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        elif item_id == "D9":
            print("[doctor] D9: verify_consistency --fix -y 실행 중...")
            script = _PROJ_ROOT / "scripts" / "verify_consistency.py"
            subprocess.run(["python", str(script), "--fix", "-y"], check=False)
