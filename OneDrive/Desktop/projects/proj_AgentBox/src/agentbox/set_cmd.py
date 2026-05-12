"""agentbox set — unified environment provisioning (7-step flow)."""
import logging
import os
import platform
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

from agentbox.init_deps import DEPS, PYTHON_PACKAGES, check_dep, check_python_pkg, try_auto_install

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger("agentbox.set")


def _setup_file_logger(log_dir: Path | None = None) -> None:
    if logger.handlers:
        return
    target = log_dir or (_PROJ_ROOT / ".agentbox" / "logs")
    target.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    handler = logging.FileHandler(target / f"agentbox-set-{timestamp}.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _log(msg: str, level: str = "info") -> None:
    print(msg)
    getattr(logger, level)(msg)


# ── Step 2: dependency check ──────────────────────────────────────────────────

def _check_deps_step(args) -> int:
    """Step 2: Check system dependencies. Returns 0 on success/skip, 4 on hard fail."""
    failed = []
    for dep in DEPS:
        ok, _err = check_dep(dep)
        _log(f"[agentbox] {dep.name}: {'OK' if ok else 'MISSING'}")
        if not ok:
            failed.append(dep)

    for pkg in PYTHON_PACKAGES:
        ok = check_python_pkg(pkg)
        _log(f"[agentbox] python package {pkg}: {'OK' if ok else 'MISSING'}")

    if not failed:
        return 0

    names = ", ".join(d.name for d in failed)
    _log(f"[agentbox] 누락된 의존성: {names}", "warning")

    if getattr(args, "skip_deps_install", False):
        _log("[agentbox] --skip-deps-install 설정됨. 경고만 출력 후 계속 진행.", "warning")
        return 0

    if not getattr(args, "yes", False):
        ans = input(f"누락된 의존성: {names}. 자동 설치할까요? [y/N]: ").strip().lower()
        if ans != "y":
            for dep in failed:
                _log(f"  수동 설치: {dep.name}")
            return 4

    for dep in failed:
        _log(f"[agentbox] Installing {dep.name} ...")
        if not try_auto_install(dep):
            _log(f"[agentbox] ERROR: {dep.name} 설치 실패.", "error")
            return 4

    return 0


# ── Step 3: env vars check ────────────────────────────────────────────────────

def _check_env_step(args, bashrc: Path) -> int:
    """Step 3: Check AWS env vars, add missing ones to ~/.bashrc."""
    env_marker = "# AgentBox environment"
    env_defaults = {"AWS_REGION": "us-east-1", "PROJECT_NAME": "agentbox"}

    existing = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
    lines_to_add = []

    for var, default in env_defaults.items():
        current_val = os.environ.get(var, "").strip()
        if current_val:
            _log(f"[agentbox] {var}={current_val} (OK)")
            continue
        if f"export {var}=" in existing:
            _log(f"[agentbox] {var} already in ~/.bashrc (OK)")
            continue
        if getattr(args, "yes", False):
            val = default
            _log(f"[agentbox] {var} 미설정. 기본값 사용: {val}")
        else:
            val = input(f"[agentbox] {var} 미설정. 값 입력 (기본: {default}): ").strip() or default
        lines_to_add.append(f"export {var}={val}")

    if lines_to_add:
        with open(bashrc, "a", encoding="utf-8") as f:
            if env_marker not in existing:
                f.write(f"\n{env_marker}\n")
            f.write("\n".join(lines_to_add) + "\n")
        _log(f"[agentbox] ~/.bashrc 에 추가: {', '.join(lines_to_add)}")
    else:
        _log("[agentbox] Step 3: 환경변수 모두 OK.")

    return 0


# ── Step 4: CA + mTLS certs ───────────────────────────────────────────────────

def _check_ca_mtls_step(layout) -> int:
    """Step 4: Ensure CA + mTLS client certs exist in global certs dir."""
    from agentbox.proxy.ca import gen_mtls_certs

    certs_dir = layout.global_certs_dir
    try:
        ca_crt, ca_key, ep_crt, ep_key = gen_mtls_certs(certs_dir)
        _log(f"[agentbox] CA cert: {ca_crt}")
        _log(f"[agentbox] endpoint cert: {ep_crt}")
    except Exception as exc:
        _log(f"[agentbox] ERROR: CA/mTLS 인증서 생성 실패: {exc}", "error")
        return 5

    result = subprocess.run(
        ["openssl", "verify", "-CAfile", "/etc/ssl/certs/ca-certificates.crt", str(ca_crt)],
        capture_output=True, timeout=10, check=False,
    )
    if result.returncode != 0:
        _log(
            "[agentbox] CA 가 시스템 trust store 에 미등록.\n"
            "  sudo bash scripts/install_ca.sh 를 실행해 주세요.",
            "warning",
        )
    else:
        _log("[agentbox] CA 시스템 trust store 등록 확인 완료.")

    return 0


# ── Step 5: proto stub ────────────────────────────────────────────────────────

def _ensure_proto_stub() -> int:
    """Step 5: Check proto stub availability; generate if missing."""
    import importlib
    try:
        importlib.import_module("agentbox.grpc.inspect_pb2")
        _log("[agentbox] proto stub: OK")
        return 0
    except ImportError:
        pass

    _log("[agentbox] proto stub 없음. grpc_tools.protoc 실행 중...", "warning")
    proto_file = _PROJ_ROOT / "grpc" / "inspect.proto"
    if not proto_file.exists():
        _log(f"[agentbox] ERROR: proto file not found: {proto_file}", "error")
        return 6

    result = subprocess.run(
        [
            "python", "-m", "grpc_tools.protoc",
            f"-I{proto_file.parent}",
            f"--python_out={_PROJ_ROOT / 'src'}",
            f"--grpc_python_out={_PROJ_ROOT / 'src'}",
            str(proto_file),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        _log(f"[agentbox] ERROR: protoc 실패 (exit {result.returncode})", "error")
        return 6

    _log("[agentbox] proto stub 생성 완료")
    return 0


# ── Step 6: shell integration ─────────────────────────────────────────────────

def _install_shell_integration(bashrc: Path) -> bool:
    """Step 6: Add agentbox shell function to ~/.bashrc.

    Returns True if newly added, False if already present.
    """
    scripts_dir = _PROJ_ROOT / "scripts"
    marker = "# AgentBox shell integration"
    integration = f"""
{marker}
unalias agentbox 2>/dev/null
agentbox() {{
    case "$1" in
        on)  source {scripts_dir}/activate.sh ;;
        off) source {scripts_dir}/deactivate.sh ;;
        *)   command agentbox "$@" ;;
    esac
}}
"""
    content = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
    if marker in content:
        return False
    with open(bashrc, "a", encoding="utf-8") as f:
        f.write(integration)
    return True


# ── Step 7a: background run + health check ────────────────────────────────────

def _start_and_health_check(layout) -> int:
    """Step 7a: Start background proxy; poll :PROXY_PORT + :API_PORT for 10 s."""
    from agentbox.config import cfg

    # If already running, skip
    for port in (cfg.PROXY_PORT, cfg.API_PORT):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                _log(f"[agentbox] 프록시 이미 실행 중 (:{port}). 생략.")
                return 0
        except OSError:
            pass

    log_file = layout.local_logs_dir / "agentbox-run.log"
    pid_file = layout.local_pid

    try:
        with open(log_file, "w") as lf:
            proc = subprocess.Popen(
                ["agentbox", "run"],
                stdout=lf, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        pid_file.write_text(str(proc.pid))
        _log(f"[agentbox] 프록시 백그라운드 시작 (pid {proc.pid})")
    except Exception as exc:
        _log(f"[agentbox] ERROR: 프록시 시작 실패: {exc}", "error")
        return 7

    # Poll for LISTEN (up to 10 s)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        ok = True
        for port in (cfg.PROXY_PORT, cfg.API_PORT):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    pass
            except OSError:
                ok = False
                break
        if ok:
            return 0
        time.sleep(0.5)

    _log(
        f"[agentbox] ERROR: :{cfg.PROXY_PORT}/:{cfg.API_PORT} LISTEN 안 됨 (10초 초과)",
        "error",
    )
    try:
        lines = log_file.read_text(errors="replace").splitlines()[-50:]
        for line in lines:
            _log(f"  {line}")
    except Exception:
        pass
    return 7


# ── Step 7b: gRPC TCP connect ─────────────────────────────────────────────────

def _check_grpc_tcp() -> int:
    """Step 7b: Verify TCP connectivity to GRPC_HOST:GRPC_PORT."""
    from agentbox.config import cfg

    host = cfg.GRPC_HOST
    if not host:
        _log("[agentbox] GRPC_HOST 미설정. Step 7b 건너뜀.", "warning")
        return 0

    port = cfg.GRPC_PORT
    try:
        with socket.create_connection((host, port), timeout=5):
            pass
        return 0
    except OSError as exc:
        _log(
            f"[agentbox] ERROR: gRPC TCP 연결 실패 ({host}:{port}): {exc}\n"
            "  1. 보안 그룹: 인바운드 포트 50051 확인\n"
            "  2. gRPC 서비스: EC2에서 systemctl status agentbox-grpc",
            "error",
        )
        return 7


# ── Step 7c: mTLS handshake ───────────────────────────────────────────────────

def _check_mtls_handshake(layout) -> int:
    """Step 7c: Verify mTLS handshake (cert trust chain, not a full RPC call)."""
    from agentbox.config import cfg
    from agentbox.grpc.handshake import verify_mtls_handshake

    host = cfg.GRPC_HOST
    if not host:
        _log("[agentbox] GRPC_HOST 미설정. Step 7c 건너뜀.", "warning")
        return 0

    port = cfg.GRPC_PORT
    ca_cert = cfg.GRPC_CA_CERT or str(layout.global_certs_dir / "agentbox-ca.crt")
    client_cert = cfg.GRPC_CLIENT_CERT or str(layout.global_certs_dir / "endpoint.crt")
    client_key = cfg.GRPC_CLIENT_KEY or str(layout.global_certs_dir / "endpoint.key")

    ok, reason = verify_mtls_handshake(host, port, ca_cert, client_cert, client_key, timeout=5)
    if ok:
        return 0

    _log(
        f"[agentbox] ERROR: mTLS handshake 실패: {reason}\n"
        "  CA/client cert 불일치 또는 EC2 mTLS 설정 점검",
        "error",
    )
    return 7


# ── Deprecated helpers (kept for backwards-compat with existing tests) ────────

def _check_ca_step() -> int:
    """Legacy Step 3 — CA only (no mTLS client cert). Kept for test compatibility."""
    from agentbox.config import cfg
    from agentbox.proxy.ca import ensure_ca

    ca_dir = Path(cfg.CA_DIR)
    if not ca_dir.is_absolute():
        ca_dir = _PROJ_ROOT / ca_dir

    ca_crt, _ = ensure_ca(ca_dir)
    _log(f"[agentbox] CA 인증서: {ca_crt}")

    result = subprocess.run(
        ["openssl", "verify", "-CAfile", "/etc/ssl/certs/ca-certificates.crt", str(ca_crt)],
        capture_output=True, timeout=10, check=False,
    )
    if result.returncode != 0:
        _log(
            "[agentbox] CA 가 시스템 trust store 에 미등록.\n"
            "  sudo bash scripts/install_ca.sh 를 실행해 주세요.",
            "warning",
        )
    else:
        _log("[agentbox] CA 시스템 trust store 등록 확인 완료.")

    return 0


def _start_proxy_background() -> None:
    """Legacy background start (no health-check). Kept for test compatibility."""
    check = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True)
    if ":8080" in check.stdout:
        _log("[agentbox] 프록시 이미 실행 중 (:8080). 생략.")
        return

    log_dir = _PROJ_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "agentbox-run.log"
    pid_file = _PROJ_ROOT / ".agentbox.pid"

    try:
        with open(log_file, "w") as lf:
            proc = subprocess.Popen(
                ["agentbox", "run"],
                stdout=lf, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        pid_file.write_text(str(proc.pid))
        _log(f"[agentbox] 프록시 백그라운드 시작 완료 (pid {proc.pid})")
        _log(f"[agentbox] 로그: {log_file}")
    except Exception as exc:
        _log(f"[agentbox] 프록시 백그라운드 시작 실패: {exc}", "warning")


# ── Main entrypoint ───────────────────────────────────────────────────────────

def run_set(args) -> int:
    if platform.system() == "Windows":
        _log("[agentbox] Windows native shell 감지. WSL 터미널 안에서 실행하세요.", "warning")
        return 0

    # Step 1: ensure layout (create dirs + one-time migration)
    from agentbox.dotagentbox import ensure_layout
    try:
        layout = ensure_layout(_PROJ_ROOT)
    except PermissionError as exc:
        print(f"[agentbox] ERROR: 레이아웃 초기화 권한 오류: {exc}")
        return 1

    _setup_file_logger(layout.local_logs_dir)
    _log("[agentbox] Step 1: 레이아웃 초기화 완료.")

    # Step 2: deps
    _log("[agentbox] Step 2: 의존성 점검...")
    rc = _check_deps_step(args)
    if rc != 0:
        return rc

    # Step 3: env vars
    _log("[agentbox] Step 3: 환경변수 점검...")
    bashrc = Path.home() / ".bashrc"
    if not bashrc.exists():
        bashrc.touch()
    _check_env_step(args, bashrc)

    # Step 4: CA + mTLS
    _log("[agentbox] Step 4: CA + mTLS 인증서 확인...")
    rc = _check_ca_mtls_step(layout)
    if rc != 0:
        return rc

    # Step 5: proto stub
    _log("[agentbox] Step 5: proto stub 확인...")
    rc = _ensure_proto_stub()
    if rc != 0:
        return rc

    # Step 6: shell integration
    _log("[agentbox] Step 6: Shell integration 등록...")
    added = _install_shell_integration(bashrc)
    if added:
        _log("[agentbox] Shell integration 추가됨 (~/.bashrc).")
    else:
        _log("[agentbox] Shell integration already installed in ~/.bashrc")

    # Step 7a: background proxy + health check
    _log("[agentbox] Step 7a: 프록시 백그라운드 시작 + LISTEN 확인...")
    rc = _start_and_health_check(layout)
    if rc != 0:
        return rc
    _log("[agentbox] Step 7a: proxy LISTEN OK")

    # Step 7b: gRPC TCP
    _log("[agentbox] Step 7b: gRPC TCP 연결 확인...")
    rc = _check_grpc_tcp()
    if rc != 0:
        return rc
    _log("[agentbox] Step 7b: gRPC TCP OK")

    # Step 7c: mTLS handshake
    _log("[agentbox] Step 7c: mTLS handshake 검증...")
    rc = _check_mtls_handshake(layout)
    if rc != 0:
        return rc
    _log("[agentbox] Step 7c: mTLS handshake OK")

    print("[agentbox] set 완료.")
    print("[agentbox]   대시보드 : http://localhost:8000")
    print("[agentbox]   비활성화 : agentbox destroy")
    print("[agentbox]   재시작   : agentbox reset")
    return 0
