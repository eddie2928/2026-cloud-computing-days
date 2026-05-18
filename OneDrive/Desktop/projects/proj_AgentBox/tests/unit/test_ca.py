import pytest
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from agentbox.proxy.ca import ensure_ca


def test_ca_generated(tmp_path):
    crt, key = ensure_ca(tmp_path)
    assert crt.exists()
    assert key.exists()


def test_ca_is_self_signed(tmp_path):
    crt, _ = ensure_ca(tmp_path)
    cert = x509.load_pem_x509_certificate(crt.read_bytes())
    assert cert.subject == cert.issuer


def test_ca_key_usage(tmp_path):
    crt, _ = ensure_ca(tmp_path)
    cert = x509.load_pem_x509_certificate(crt.read_bytes())
    ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    assert ku.digital_signature is True
    assert ku.key_cert_sign is True


def test_ca_idempotent(tmp_path):
    crt1, key1 = ensure_ca(tmp_path)
    data1 = crt1.read_bytes()
    crt2, key2 = ensure_ca(tmp_path)
    data2 = crt2.read_bytes()
    assert data1 == data2  # no regeneration on second call


def test_mitmproxy_pem_cert_matches_ca_crt(tmp_path):
    crt, _ = ensure_ca(tmp_path)
    pem_path = tmp_path / "mitmproxy-ca.pem"

    ca_cert = x509.load_pem_x509_certificate(crt.read_bytes())

    pem_bytes = pem_path.read_bytes()
    cert_start = pem_bytes.find(b"-----BEGIN CERTIFICATE-----")
    assert cert_start >= 0, "No certificate block in mitmproxy-ca.pem"
    pem_cert = x509.load_pem_x509_certificate(pem_bytes[cert_start:])

    assert ca_cert.fingerprint(hashes.SHA256()) == pem_cert.fingerprint(hashes.SHA256())
