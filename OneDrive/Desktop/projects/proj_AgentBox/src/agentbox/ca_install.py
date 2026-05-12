"""Install AgentBox CA certificate into the system trust store."""
import subprocess
import sys
from pathlib import Path


def install_to_trust_store(ca_cert: Path) -> int:
    """Copy ca_cert to system trust store and run update-ca-certificates.

    Returns 0 on success, 1 if sudo not available (prints hint instead).
    """
    if not ca_cert.exists():
        print(f"[agentbox] ERROR: CA cert not found: {ca_cert}", file=sys.stderr)
        return 1

    # Check sudo availability
    sudo_check = subprocess.run(
        ["sudo", "-n", "true"], capture_output=True
    )
    if sudo_check.returncode != 0:
        print(
            f"[agentbox] CA not installed (sudo required).\n"
            f"  Run manually:\n"
            f"    sudo cp {ca_cert} /usr/local/share/ca-certificates/agentbox-ca.crt\n"
            f"    sudo update-ca-certificates",
        )
        return 0  # Warning only, not a fatal error

    dest = Path("/usr/local/share/ca-certificates/agentbox-ca.crt")
    subprocess.run(["sudo", "cp", str(ca_cert), str(dest)], check=True)
    subprocess.run(["sudo", "update-ca-certificates"], check=True)
    print("[agentbox] CA installed into system trust store.")
    return 0
