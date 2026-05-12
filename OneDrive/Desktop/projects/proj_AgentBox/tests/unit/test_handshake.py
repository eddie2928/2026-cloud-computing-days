"""Unit tests for agentbox.grpc.handshake.verify_mtls_handshake (Task-7 B5)."""
import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


# ── helpers ──────────────────────────────────────────────────────────────────
def _make_ca(tmp_path: Path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test CA")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    ca_key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    ca_cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    ca_key = tmp_path / "ca.key"
    ca_crt = tmp_path / "ca.crt"
    ca_key.write_bytes(ca_key_pem)
    ca_crt.write_bytes(ca_cert_pem)
    return ca_crt, ca_key, key, cert


def _make_client_cert(tmp_path: Path, ca_cert_obj, ca_key_obj, days: int = 365):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Client")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(ca_cert_obj.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key_obj, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    ep_key = tmp_path / "ep.key"
    ep_crt = tmp_path / "ep.crt"
    ep_key.write_bytes(key_pem)
    ep_crt.write_bytes(cert_pem)
    return ep_crt, ep_key


# ── T1: TCP OK + gRPC ready → True ───────────────────────────────────────────
def test_handshake_success(tmp_path):
    ca_crt, ca_key, ca_key_obj, ca_cert_obj = _make_ca(tmp_path)
    ep_crt, ep_key = _make_client_cert(tmp_path, ca_cert_obj, ca_key_obj, days=365)

    with patch("agentbox.grpc.handshake.socket.create_connection"), \
         patch("agentbox.grpc.handshake.grpc") as mock_grpc:
        mock_grpc.ssl_channel_credentials.return_value = MagicMock()
        mock_ch = MagicMock()
        mock_grpc.secure_channel.return_value = mock_ch
        mock_future = MagicMock()
        mock_future.result.return_value = None  # success
        mock_grpc.channel_ready_future.return_value = mock_future

        from agentbox.grpc.handshake import verify_mtls_handshake
        ok, reason = verify_mtls_handshake(
            "fake", 50051, str(ca_crt), str(ep_crt), str(ep_key), timeout=5
        )

    assert ok is True
    assert reason == ""


# ── T2: 만료된 client cert → pre-check → False + "expired" ──────────────────
def test_expired_cert_detected(tmp_path):
    ca_crt, ca_key, ca_key_obj, ca_cert_obj = _make_ca(tmp_path)
    # Create cert that expired 1 day ago
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Expired")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(ca_cert_obj.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=2))
        .not_valid_after(now - datetime.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(ca_key_obj, hashes.SHA256())
    )
    ep_key_path = tmp_path / "exp.key"
    ep_crt_path = tmp_path / "exp.crt"
    ep_key_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
    )
    ep_crt_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    from agentbox.grpc.handshake import verify_mtls_handshake
    ok, reason = verify_mtls_handshake(
        "fake", 50051, str(ca_crt), str(ep_crt_path), str(ep_key_path), timeout=5
    )

    assert ok is False
    assert "expired" in reason.lower()


# ── T3: TCP OK, gRPC FutureTimeoutError → False + "CA mismatch" ──────────────
def test_ca_mismatch(tmp_path):
    ca_crt, ca_key, ca_key_obj, ca_cert_obj = _make_ca(tmp_path)
    ep_crt, ep_key = _make_client_cert(tmp_path, ca_cert_obj, ca_key_obj, days=365)

    class FakeTimeoutError(Exception):
        pass

    with patch("agentbox.grpc.handshake.socket.create_connection"), \
         patch("agentbox.grpc.handshake.grpc") as mock_grpc:
        mock_grpc.ssl_channel_credentials.return_value = MagicMock()
        mock_ch = MagicMock()
        mock_grpc.secure_channel.return_value = mock_ch
        mock_future = MagicMock()
        # Name the exception class so "timeout" appears in __name__
        FakeTimeoutError.__name__ = "FutureTimeoutError"
        mock_future.result.side_effect = FakeTimeoutError("deadline exceeded")
        mock_grpc.channel_ready_future.return_value = mock_future

        from agentbox.grpc.handshake import verify_mtls_handshake
        ok, reason = verify_mtls_handshake(
            "fake", 50051, str(ca_crt), str(ep_crt), str(ep_key), timeout=5
        )

    assert ok is False
    assert "mismatch" in reason.lower() or "ca" in reason.lower()


# ── T4: TCP unreachable → False + "unreachable" ───────────────────────────────
def test_host_unreachable(tmp_path):
    ca_crt, ca_key, ca_key_obj, ca_cert_obj = _make_ca(tmp_path)
    ep_crt, ep_key = _make_client_cert(tmp_path, ca_cert_obj, ca_key_obj, days=365)

    import socket as _socket
    with patch("agentbox.grpc.handshake.socket.create_connection",
               side_effect=OSError("Connection refused")):
        from agentbox.grpc.handshake import verify_mtls_handshake
        ok, reason = verify_mtls_handshake(
            "fake", 50051, str(ca_crt), str(ep_crt), str(ep_key), timeout=5
        )

    assert ok is False
    assert "unreachable" in reason.lower()
