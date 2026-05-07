import asyncio
import re
import subprocess
from pathlib import Path

from loguru import logger

_POLL_INTERVAL = 5  # seconds


async def run_stats_loop(log_path: str) -> None:
    """1A-8: Export iptables redirect counters every 5 seconds to log_path."""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    log_file = Path(log_path)

    while True:
        try:
            stats = _read_iptables_stats()
            line = f"pkts={stats['pkts']} bytes={stats['bytes']}\n"
            with open(log_file, "a") as f:
                f.write(line)
        except Exception as exc:
            logger.debug("ebpf_stats_error", error=str(exc))
        await asyncio.sleep(_POLL_INTERVAL)


def _read_iptables_stats() -> dict:
    """Parse packet/byte counters for the AgentBox REDIRECT rule."""
    result = subprocess.run(
        ["iptables", "-t", "nat", "-L", "OUTPUT", "-v", "-n", "--line-numbers"],
        capture_output=True, text=True, timeout=3,
    )
    for line in result.stdout.splitlines():
        if "REDIRECT" in line and "443" in line:
            parts = line.split()
            # Output format: num pkts bytes target ...
            if len(parts) >= 3:
                return {"pkts": parts[1], "bytes": parts[2]}
    return {"pkts": "0", "bytes": "0"}
