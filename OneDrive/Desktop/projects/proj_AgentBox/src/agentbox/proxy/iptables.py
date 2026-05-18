"""iptables OUTPUT chain REDIRECT rules for routing specific HTTPS traffic to mitmproxy."""
import subprocess
import sys
from pathlib import Path

_DEFAULT_HOSTS = ["api.anthropic.com"]
_HOSTS_FILE = Path.home() / ".agentbox" / "redirect_hosts"


def load_redirect_hosts() -> list[str]:
    """Return default hosts plus any extra hosts from ~/.agentbox/redirect_hosts."""
    hosts = list(_DEFAULT_HOSTS)
    if _HOSTS_FILE.exists():
        for line in _HOSTS_FILE.read_text().splitlines():
            host = line.strip()
            if host and host not in hosts:
                hosts.append(host)
    return hosts


def _run(args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "permission" in stderr.lower() or "operation not permitted" in stderr.lower():
            print(
                "[agentbox] iptables 권한 오류: sudo 권한이 필요합니다.\n"
                "  sudo agentbox on  또는  sudo -E agentbox on",
                file=sys.stderr,
            )
        raise PermissionError(f"iptables failed: {stderr or result.stdout.strip()}")
    return result


def _rule_args(proxy_port: int, host: str, action: str) -> list[str]:
    return [
        "iptables", "-t", "nat", action, "OUTPUT",
        "-p", "tcp", "--dport", "443",
        "-m", "string", "--algo", "bm", "--string", host,
        "-j", "REDIRECT", "--to-ports", str(proxy_port),
    ]


def apply_redirect(proxy_port: int, target_hosts: list[str]) -> None:
    for host in target_hosts:
        _run(_rule_args(proxy_port, host, "-A"))


def _list_redirect_hosts(proxy_port: int) -> list[str]:
    """Return hosts currently redirected to proxy_port via iptables nat OUTPUT."""
    result = subprocess.run(
        ["iptables", "-t", "nat", "-L", "OUTPUT", "-n"],
        capture_output=True, text=True,
    )
    hosts = []
    for line in result.stdout.splitlines():
        if f"to:{proxy_port}" in line or f"ports {proxy_port}" in line:
            # Extract quoted string (the host matcher)
            if '"' in line:
                start = line.index('"') + 1
                end = line.index('"', start)
                hosts.append(line[start:end])
    return hosts


def clear_redirect(proxy_port: int) -> None:
    for host in _list_redirect_hosts(proxy_port):
        try:
            _run(_rule_args(proxy_port, host, "-D"))
        except PermissionError:
            raise
        except Exception:
            pass
