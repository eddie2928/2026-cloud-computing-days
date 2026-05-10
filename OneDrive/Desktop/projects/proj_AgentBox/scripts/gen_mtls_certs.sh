#!/usr/bin/env bash
# 1B-3: Generate mTLS certificates for AgentBox gRPC (self-signed CA)
# Usage: bash scripts/gen_mtls_certs.sh [output_dir]
# Output: agentbox-ca.crt, endpoint.crt, endpoint.key, ec2.crt, ec2.key
set -e

OUT="${1:-certs/grpc}"
mkdir -p "$OUT"

echo "[agentbox] Generating mTLS CA ..."
python3 - "$OUT" <<'PYEOF'
import os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

OUT = sys.argv[1] if len(sys.argv) > 1 else "certs/grpc"
Path(OUT).mkdir(parents=True, exist_ok=True)

def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)

def _save_key(k, path):
    Path(path).write_bytes(k.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

def _save_cert(c, path):
    Path(path).write_bytes(c.public_bytes(serialization.Encoding.PEM))

now = datetime.now(timezone.utc)

# CA
ca_key = _key()
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AgentBox mTLS CA")])
ca_cert = (
    x509.CertificateBuilder()
    .subject_name(ca_name).issuer_name(ca_name)
    .public_key(ca_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now).not_valid_after(now + timedelta(days=3650))
    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    .sign(ca_key, hashes.SHA256())
)
_save_key(ca_key, f"{OUT}/agentbox-ca.key")
_save_cert(ca_cert, f"{OUT}/agentbox-ca.crt")

def _leaf(cn, san_dns=None):
    key = _key()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(ca_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    )
    sans = [x509.DNSName(cn)]
    if san_dns:
        sans.append(x509.DNSName(san_dns))
    builder = builder.add_extension(x509.SubjectAlternativeName(sans), critical=False)
    cert = builder.sign(ca_key, hashes.SHA256())
    return key, cert

# Endpoint (WSL2 client)
ep_key, ep_cert = _leaf("agentbox-endpoint")
_save_key(ep_key, f"{OUT}/endpoint.key")
_save_cert(ep_cert, f"{OUT}/endpoint.crt")

# EC2 server
ec2_key, ec2_cert = _leaf("agentbox-ec2")
_save_key(ec2_key, f"{OUT}/ec2.key")
_save_cert(ec2_cert, f"{OUT}/ec2.crt")

print(f"Certificates written to {OUT}/")
for f in ["agentbox-ca.crt", "endpoint.crt", "endpoint.key", "ec2.crt", "ec2.key"]:
    print(f"  {OUT}/{f}")
PYEOF
