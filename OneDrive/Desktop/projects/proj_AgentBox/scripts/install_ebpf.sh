#!/usr/bin/env bash
# 1A-2: eBPF / BCC tools install on Ubuntu 22.04
# Run inside the dev VM (or WSL2): sudo bash scripts/install_ebpf.sh
# Completion check: python3 -c "from bcc import BPF"

set -e

KERNEL=$(uname -r)
echo "[agentbox] Installing eBPF toolchain for kernel $KERNEL ..."

apt-get update -qq
apt-get install -y \
    "linux-headers-${KERNEL}" \
    bpfcc-tools \
    clang \
    llvm \
    libbpf-dev \
    python3-bpfcc \
    build-essential \
    pkg-config

echo "[agentbox] Verifying BCC import ..."
python3 -c "from bcc import BPF; print('BCC OK')"

echo "[agentbox] Verifying bpftool ..."
bpftool feature | head -5

echo ""
echo "  eBPF toolchain installed successfully."
echo "  Next: sudo bash /agentbox/scripts/iptables_redirect.sh on"
