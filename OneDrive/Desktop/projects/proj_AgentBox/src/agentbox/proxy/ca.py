import datetime
import ipaddress
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
        if not pem_path.exists():
            pem_path.write_bytes(key_path.read_bytes() + crt_path.read_bytes())
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


def gen_mtls_certs(
    certs_dir: Path,
    ips: list[str] | None = None,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    """Ensure CA + mTLS client cert + server cert exist in certs_dir.

    Returns:
        (ca_crt, ca_key, endpoint_crt, endpoint_key, ec2_crt, ec2_key)
    """
    ca_crt, ca_key = ensure_ca(certs_dir)

    endpoint_crt_path = certs_dir / "endpoint.crt"
    endpoint_key_path = certs_dir / "endpoint.key"
    ec2_crt_path = certs_dir / "ec2.crt"
    ec2_key_path = certs_dir / "ec2.key"

    need_endpoint = not (endpoint_crt_path.exists() and endpoint_key_path.exists())
    need_ec2 = not (ec2_crt_path.exists() and ec2_key_path.exists())

    if not need_endpoint and not need_ec2:
        return ca_crt, ca_key, endpoint_crt_path, endpoint_key_path, ec2_crt_path, ec2_key_path

    ca_cert_obj = x509.load_pem_x509_certificate(ca_crt.read_bytes())
    ca_private_key = serialization.load_pem_private_key(ca_key.read_bytes(), password=None)
    now = datetime.datetime.now(datetime.timezone.utc)

    if need_endpoint:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "AgentBox mTLS Client"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AgentBox"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(ca_cert_obj.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(ca_private_key, hashes.SHA256())
        )
        endpoint_key_path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
        endpoint_crt_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    if need_ec2:
        san_names: list[x509.GeneralName] = [
            x509.DNSName("agentbox-ec2"),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
        for ip_str in (ips or []):
            san_names.append(x509.IPAddress(ipaddress.ip_address(ip_str)))

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "AgentBox EC2 Server"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AgentBox"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(ca_cert_obj.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
            .sign(ca_private_key, hashes.SHA256())
        )
        ec2_key_path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
        ec2_crt_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    return ca_crt, ca_key, endpoint_crt_path, endpoint_key_path, ec2_crt_path, ec2_key_path
