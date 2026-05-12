"""Dependency matrix for agentbox init."""
import importlib.metadata
import platform
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Dep:
    name: str
    check_cmd: list
    install_hint_linux: str
    install_hint_macos: str
    install_hint_windows: str
    required: bool = True


DEPS = [
    Dep(
        "sops",
        ["sops", "--version"],
        install_hint_linux=(
            "curl -fsSL https://github.com/getsops/sops/releases/download/v3.12.2/"
            "sops-v3.12.2.linux.amd64 -o /usr/local/bin/sops && chmod +x /usr/local/bin/sops"
        ),
        install_hint_macos="brew install sops",
        install_hint_windows="winget install -e --id Mozilla.Sops",
    ),
    Dep(
        "aws",
        ["aws", "--version"],
        install_hint_linux="sudo apt-get install -y awscli",
        install_hint_macos="brew install awscli",
        install_hint_windows="winget install -e --id Amazon.AWSCLI",
    ),
]

# Runtime Python packages required by agentbox.
# grpcio-tools is needed to regenerate proto stubs when the installed
# protobuf runtime version differs from the committed pb2 gencode version.
PYTHON_PACKAGES = ["boto3", "pyyaml", "grpcio-tools"]


def check_dep(dep: Dep) -> tuple[bool, str | None]:
    try:
        result = subprocess.run(dep.check_cmd, capture_output=True, timeout=5)
        if result.returncode == 0:
            return True, None
        return False, result.stderr.decode()[:200]
    except Exception as exc:
        return False, str(exc)[:200]


def check_python_pkg(name: str) -> bool:
    try:
        importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def _install_hint(dep: Dep) -> str:
    system = platform.system()
    if system == "Darwin":
        return dep.install_hint_macos
    if system == "Windows":
        return dep.install_hint_windows
    return dep.install_hint_linux


def try_auto_install(dep: Dep) -> bool:
    hint = _install_hint(dep)
    try:
        subprocess.run(hint, shell=True, timeout=120)
    except Exception:
        return False
    ok, _ = check_dep(dep)
    return ok


def try_auto_install_pkg(name: str) -> bool:
    """Install a Python package via pip into the current interpreter's environment."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", name],
            timeout=120,
        )
        return result.returncode == 0 and check_python_pkg(name)
    except Exception:
        return False
