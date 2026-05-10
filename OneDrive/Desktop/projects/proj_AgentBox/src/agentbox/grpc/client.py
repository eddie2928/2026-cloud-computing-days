"""1B-2: gRPC client with connection pool and mTLS support."""
import grpc

from agentbox.config import cfg
from agentbox.grpc import inspect_pb2, inspect_pb2_grpc

_MAX_CONNECTIONS = 5
_pool: list[grpc.Channel] = []
_pool_idx = 0


def _make_channel() -> grpc.Channel:
    target = f"{cfg.GRPC_HOST}:{cfg.GRPC_PORT}"
    if cfg.GRPC_CA_CERT and cfg.GRPC_CLIENT_CERT and cfg.GRPC_CLIENT_KEY:
        # 1B-3: mTLS using endpoint client cert + CA cert for server verification
        with open(cfg.GRPC_CA_CERT, "rb") as f:
            root_certs = f.read()
        with open(cfg.GRPC_CLIENT_CERT, "rb") as f:
            cert_chain = f.read()
        with open(cfg.GRPC_CLIENT_KEY, "rb") as f:
            private_key = f.read()
        creds = grpc.ssl_channel_credentials(
            root_certificates=root_certs,
            private_key=private_key,
            certificate_chain=cert_chain,
        )
        # Server cert SAN is DNS:agentbox-ec2; override when connecting by IP
        options = [("grpc.ssl_target_name_override", "agentbox-ec2")]
        return grpc.secure_channel(target, creds, options=options)
    return grpc.insecure_channel(target)


def _get_channel() -> grpc.Channel:
    global _pool_idx
    if len(_pool) < _MAX_CONNECTIONS:
        _pool.append(_make_channel())
    ch = _pool[_pool_idx % len(_pool)]
    _pool_idx += 1
    return ch


def inspect(user_id: str, prompt: str, model: str = "") -> inspect_pb2.InspectResponse:
    """Call EC2 Inspector.Inspect RPC. Raises grpc.RpcError on failure."""
    stub = inspect_pb2_grpc.InspectorStub(_get_channel())
    request = inspect_pb2.InspectRequest(user_id=user_id, prompt=prompt, model=model)
    return stub.Inspect(request, timeout=cfg.GRPC_TIMEOUT)
