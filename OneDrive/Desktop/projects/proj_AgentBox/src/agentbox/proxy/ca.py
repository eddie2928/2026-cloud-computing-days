import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def ensure_ca(ca_dir: Path) -> tuple[Path, Path]:
    ca_dir.mkdir(parents=True, exist_ok=True)
    crt_path = ca_dir / "agentbox-ca.crt"
    key_path = ca_dir / "agentbox-ca.key"
    pem_path = ca_dir / "mitmproxy-ca.pem"

    if crt_path.exists() and key_path.exists():
        return crt_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "AgentBox Local CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AgentBox"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)

    key_path.write_bytes(key_pem)
    crt_path.write_bytes(cert_pem)
    # mitmproxy expects key + cert combined in one PEM file
    pem_path.write_bytes(key_pem + cert_pem)

    return crt_path, key_path
