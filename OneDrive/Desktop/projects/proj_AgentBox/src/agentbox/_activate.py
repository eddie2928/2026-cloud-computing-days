"""on/off subcommand handlers — HTTPS_PROXY activation via eval pattern.

Shell integration in ~/.bashrc calls:
    eval "$(command agentbox _on)"   # on
    eval "$(command agentbox _off)"  # off

stdout is ONLY eval-safe export/unset statements.
All user-facing messages go to stderr.
"""
import os
import socket
import subprocess
import sys
from pathlib import Path

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


def _is_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


_DEFAULT_REDIRECT_HOSTS = ["api.anthropic.com"]


def _apply_iptables(proxy_port: int) -> None:
    try:
        from agentbox.proxy.iptables import apply_redirect
        apply_redirect(proxy_port, _DEFAULT_REDIRECT_HOSTS)
    except Exception as exc:
        print(f"[agentbox] iptables 설정 건너뜀 (Linux/WSL + sudo 필요): {exc}", file=sys.stderr)


def _clear_iptables(proxy_port: int) -> None:
    try:
        from agentbox.proxy.iptables import clear_redirect
        clear_redirect(proxy_port)
    except Exception as exc:
        print(f"[agentbox] iptables 해제 건너뜀: {exc}", file=sys.stderr)


def on_command(project_root: Path | None = None, no_iptables: bool = False) -> int:
    """Print export statements to stdout; start proxy if needed (stderr)."""
    from agentbox.dotagentbox import ensure_layout
    from agentbox.config import cfg

    root = project_root or _PROJ_ROOT
    layout = ensure_layout(root)

    if not _is_listening(cfg.PROXY_PORT):
        print("[agentbox] 프록시 시작 중...", file=sys.stderr)
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
            print(f"[agentbox] 프록시 백그라운드 시작 (pid {proc.pid})", file=sys.stderr)
        except Exception as exc:
            print(f"[agentbox] ERROR: 프록시 시작 실패: {exc}", file=sys.stderr)
    else:
        print("[agentbox] 프록시 이미 실행 중 (:8080).", file=sys.stderr)

    if not no_iptables:
        _apply_iptables(cfg.PROXY_PORT)

    ca_cert = layout.global_certs_dir / "agentbox-ca.crt"
    proxy_port = cfg.PROXY_PORT

    # stdout: only valid shell commands (eval target)
    print(f"export HTTPS_PROXY=http://127.0.0.1:{proxy_port}")
    print("export NO_PROXY=169.254.169.254,amazonaws.com,aws.amazon.com,s3.amazonaws.com")
    print(f"export NODE_EXTRA_CA_CERTS={ca_cert}")

    return 0


def off_command(project_root: Path | None = None, no_iptables: bool = False) -> int:
    """Print unset statements to stdout; stop proxy via pid file (stderr)."""
    from agentbox.dotagentbox import ensure_layout
    from agentbox.config import cfg

    root = project_root or _PROJ_ROOT
    layout = ensure_layout(root)

    pid_file = layout.local_pid
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 15)  # SIGTERM
            pid_file.unlink(missing_ok=True)
            print(f"[agentbox] 프록시 종료 (pid {pid})", file=sys.stderr)
        except Exception as exc:
            print(f"[agentbox] 프록시 종료 실패: {exc}", file=sys.stderr)
    else:
        print("[agentbox] 실행 중인 프록시 없음.", file=sys.stderr)

    if not no_iptables:
        _clear_iptables(cfg.PROXY_PORT)

    # stdout: only valid shell commands (eval target)
    print("unset HTTPS_PROXY")
    print("unset NO_PROXY")
    print("unset NODE_EXTRA_CA_CERTS")

    return 0
