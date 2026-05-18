"""mTLS handshake verification helper shared by agentbox set (7c) and doctor (D7)."""
import socket
from datetime import datetime, timezone
from pathlib import Path

import grpc


def verify_mtls_handshake(
    host: str,
    port: int,
    ca_cert: str,
    client_cert: str,
    client_key: str,
    timeout: float = 10.0,
) -> tuple[bool, str]:
    """Verify mTLS handshake with a gRPC server.

    Strategy:
      1. Pre-check client cert expiry.
      2. TCP reachability probe — returns "unreachable" immediately on failure.
      3. Attempt grpc.channel_ready_future; timeout after TCP success → "CA mismatch".

    Returns:
        (success, reason) where reason is "" on success or a short label on failure.
    """
    # Pre-check: client cert expiry
    try:
        from cryptography import x509 as cx509
        cert_data = Path(client_cert).read_bytes()
        cert_obj = cx509.load_pem_x509_certificate(cert_data)
        if cert_obj.not_valid_after_utc < datetime.now(timezone.utc):
            return False, f"expired: client cert expired on {cert_obj.not_valid_after_utc}"
    except Exception:
        pass  # Let gRPC surface the real error

    # TCP reachability probe
    try:
        with socket.create_connection((host, port), timeout=min(timeout, 3.0)):
            pass
    except OSError as exc:
        return False, f"unreachable: {exc}"

    # mTLS handshake via gRPC channel ready future
    try:
        ca_data = Path(ca_cert).read_bytes()
        cert_data = Path(client_cert).read_bytes()
        key_data = Path(client_key).read_bytes()

        credentials = grpc.ssl_channel_credentials(
            root_certificates=ca_data,
            private_key=key_data,
            certificate_chain=cert_data,
        )
        channel = grpc.secure_channel(f"{host}:{port}", credentials)
        try:
            grpc.channel_ready_future(channel).result(timeout=timeout)
        finally:
            channel.close()
        return True, ""
    except Exception as exc:
        # FutureTimeoutError after TCP success → cert/CA issue
        msg = str(exc).lower()
        if "timeout" in type(exc).__name__.lower() or "futuredeadline" in msg:
            return False, "CA mismatch"
        if "san" in msg or "hostname" in msg or "subject alternative name" in msg:
            return False, f"SAN mismatch: {exc}"
        if "certificate" in msg or "ca" in msg or "ssl" in msg:
            return False, f"CA mismatch: {exc}"
        return False, f"unreachable: {exc}"
