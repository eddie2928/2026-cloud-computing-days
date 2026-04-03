#!/bin/bash
# Auto-install missing CLI security tools for web-bug-bounty skill
# Supports: Linux, macOS, WSL on Windows

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_and_install() {
    local tool=$1
    local install_cmd=$2
    local check_cmd=${3:-$tool}

    if command -v "$check_cmd" &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} $tool is already installed"
        return 0
    fi

    echo -e "${YELLOW}[INSTALLING]${NC} $tool..."
    if eval "$install_cmd"; then
        echo -e "${GREEN}[OK]${NC} $tool installed successfully"
    else
        echo -e "${RED}[FAIL]${NC} Failed to install $tool. Install manually: $install_cmd"
        return 1
    fi
}

echo "=== Web Bug Bounty Tool Dependency Check ==="
echo ""

# Check for Go (needed for ProjectDiscovery tools)
if ! command -v go &> /dev/null; then
    echo -e "${RED}[REQUIRED]${NC} Go is not installed. Install from https://go.dev/dl/"
    echo "ProjectDiscovery tools (subfinder, httpx, nuclei, ffuf) require Go."
    HAS_GO=false
else
    echo -e "${GREEN}[OK]${NC} Go is installed: $(go version)"
    HAS_GO=true
fi

# Check for Python/pip
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[REQUIRED]${NC} Python3 is not installed."
    HAS_PY=false
else
    echo -e "${GREEN}[OK]${NC} Python3 is installed: $(python3 --version)"
    HAS_PY=true
fi

echo ""
echo "--- Go-based tools ---"

if $HAS_GO; then
    check_and_install "subfinder" \
        "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"

    check_and_install "httpx" \
        "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest"

    check_and_install "nuclei" \
        "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"

    check_and_install "ffuf" \
        "go install -v github.com/ffuf/ffuf/v2@latest"
else
    echo -e "${YELLOW}[SKIP]${NC} Skipping Go tools (Go not installed)"
fi

echo ""
echo "--- Python-based tools ---"

if $HAS_PY; then
    check_and_install "sqlmap" \
        "pip install sqlmap" \
        "sqlmap"

    check_and_install "arjun" \
        "pip install arjun" \
        "arjun"
else
    echo -e "${YELLOW}[SKIP]${NC} Skipping Python tools (Python not installed)"
fi

echo ""
echo "--- System tools ---"

check_and_install "nmap" \
    "echo 'Install nmap from https://nmap.org/download or via package manager'" \
    "nmap"

check_and_install "curl" \
    "echo 'Install curl via package manager'" \
    "curl"

echo ""
echo "=== Dependency check complete ==="
