"""1C-3: EC2 gRPC Inspector server - regex 1차 필터 + Bedrock Agent InvokeAgent."""
import asyncio
import hashlib
import json
import os
import time
import uuid
from concurrent import futures
from datetime import datetime, timezone, timedelta

import boto3
import grpc
import requests
import yaml
from loguru import logger

# Add project root to path for proto imports
import sys
sys.path.insert(0, "/opt/agentbox")

from ec2.grpc_server.rules_engine import load_rules, check_rules

# Re-use proto stubs (shared with endpoint)
sys.path.insert(0, "/opt/agentbox/src")
from agentbox.grpc import inspect_pb2, inspect_pb2_grpc

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_PROJECT = os.environ.get("PROJECT_NAME", "agentbox")
_BEDROCK_AGENT_ID = os.environ.get("BEDROCK_AGENT_ID", "")
_BEDROCK_AGENT_ALIAS = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
_BEDROCK_MAX_TOKENS_PER_DAY = int(os.environ.get("BEDROCK_MAX_TOKENS_PER_DAY", "100000"))
_PROMPT_MAX_CHARS = int(os.environ.get("PROMPT_MAX_CHARS", "8000"))
_MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://localhost:8443")

_rules = load_rules()
_dynamodb = boto3.resource("dynamodb", region_name=_REGION)
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=_REGION)


def _daily_token_count() -> int:
    """Read today's Bedrock token usage from DynamoDB settings table."""
    table = _dynamodb.Table(f"{_PROJECT}-settings")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resp = table.get_item(Key={"key": f"bedrock_tokens_{today}"})
    return int(resp.get("Item", {}).get("value", 0))


def _increment_token_count(tokens: int) -> None:
    table = _dynamodb.Table(f"{_PROJECT}-settings")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    table.update_item(
        Key={"key": f"bedrock_tokens_{today}"},
        UpdateExpression="ADD #v :inc",
        ExpressionAttributeNames={"#v": "value"},
        ExpressionAttributeValues={":inc": tokens},
    )


def _invoke_bedrock_agent(prompt: str, session_id: str) -> tuple[str, list[str]]:
    """Call Bedrock Agent and parse verdict JSON from response."""
    chunks = []
    response = _bedrock_runtime.invoke_agent(
        agentId=_BEDROCK_AGENT_ID,
        agentAliasId=_BEDROCK_AGENT_ALIAS,
        sessionId=session_id,
        inputText=prompt,
    )
    for event in response["completion"]:
        if "chunk" in event:
            chunks.append(event["chunk"]["bytes"].decode())

    full_text = "".join(chunks)
    try:
        # Find JSON in response text
        start = full_text.find("{")
        end = full_text.rfind("}") + 1
        data = json.loads(full_text[start:end])
        verdict = data.get("verdict", "BLOCK").upper()
        reasons = data.get("reasons", [])
    except Exception:
        logger.warning("bedrock_parse_error", raw=full_text[:200])
        verdict, reasons = "BLOCK", ["Bedrock 응답 파싱 실패"]

    tokens_used = sum(len(c) for c in chunks) // 4 + len(prompt) // 4
    _increment_token_count(tokens_used)

    return verdict, reasons


def _record_event(event_id: str, user_id: str, prompt: str, verdict: str,
                  reasons: list, matched_rules: list, latency_ms: int) -> None:
    table = _dynamodb.Table(f"{_PROJECT}-events")
    now = datetime.now(timezone.utc)
    table.put_item(Item={
        "event_id": event_id,
        "ts": now.isoformat(),
        "user_id": user_id,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
        "verdict": verdict,
        "reasons_json": json.dumps(reasons),
        "matched_rules": json.dumps(matched_rules),
        "latency_ms": latency_ms,
        # TTL 365 days
        "expires_at": int((now + timedelta(days=365)).timestamp()),
    })


class InspectorServicer(inspect_pb2_grpc.InspectorServicer):
    def Inspect(self, request, context):
        event_id = uuid.uuid4().hex
        t0 = time.monotonic()
        prompt = request.prompt
        user_id = request.user_id or "unknown"

        logger.info("inspect_start", event_id=event_id, user_id=user_id,
                    prompt_len=len(prompt))

        # 1C-3 step 1: Prompt length guard
        if len(prompt) > _PROMPT_MAX_CHARS:
            verdict = "BLOCK"
            reasons = ["프롬프트 길이 제한 초과"]
            _record_event(event_id, user_id, prompt, verdict, reasons, [], 0)
            return inspect_pb2.InspectResponse(
                verdict=verdict, reasons=reasons, event_id=event_id
            )

        # 1C-3 step 2: Regex 1차 필터
        rule_matches = check_rules(prompt, _rules)
        if rule_matches:
            verdict = "BLOCK"
            reasons = [m.reason for m in rule_matches]
            matched_ids = [m.rule_id for m in rule_matches]
            latency_ms = int((time.monotonic() - t0) * 1000)
            logger.info("regex_block", event_id=event_id, rules=matched_ids)
            _record_event(event_id, user_id, prompt, verdict, reasons, matched_ids, latency_ms)
            return inspect_pb2.InspectResponse(
                verdict=verdict, reasons=reasons, event_id=event_id
            )

        # 1C-3 step 3: Bedrock Agent InvokeAgent (if configured and under token cap)
        if _BEDROCK_AGENT_ID and _daily_token_count() < _BEDROCK_MAX_TOKENS_PER_DAY:
            try:
                verdict, reasons = _invoke_bedrock_agent(prompt, event_id)
            except Exception as exc:
                logger.error("bedrock_error", event_id=event_id, error=str(exc))
                # Fallback to regex-only ALLOW if no regex match
                verdict, reasons = "ALLOW", []
        else:
            verdict, reasons = "ALLOW", []
            if not _BEDROCK_AGENT_ID:
                logger.warning("bedrock_not_configured", event_id=event_id)

        try:
            requests.delete(
                f"{_MCP_SERVER_URL}/mcp/cleanup/{event_id}",
                headers={"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"},
                timeout=5,
            )
        except Exception as exc:
            logger.warning("mcp_cleanup_failed", event_id=event_id, error=str(exc))

        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.info("inspect_done", event_id=event_id, verdict=verdict,
                    latency_ms=latency_ms)

        _record_event(event_id, user_id, prompt, verdict, reasons, [], latency_ms)
        return inspect_pb2.InspectResponse(
            verdict=verdict, reasons=reasons, event_id=event_id
        )


def serve() -> None:
    certs_dir = os.environ.get("GRPC_CERTS_DIR", "/opt/agentbox/certs/grpc")
    port = int(os.environ.get("GRPC_PORT", "50051"))

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inspect_pb2_grpc.add_InspectorServicer_to_server(InspectorServicer(), server)

    ca_crt = f"{certs_dir}/agentbox-ca.crt"
    ec2_crt = f"{certs_dir}/ec2.crt"
    ec2_key = f"{certs_dir}/ec2.key"

    if os.path.exists(ec2_crt):
        with open(ca_crt, "rb") as f:
            root_certs = f.read()
        with open(ec2_crt, "rb") as f:
            cert_chain = f.read()
        with open(ec2_key, "rb") as f:
            private_key = f.read()
        creds = grpc.ssl_server_credentials(
            [(private_key, cert_chain)],
            root_certificates=root_certs,
            require_client_auth=True,
        )
        server.add_secure_port(f"0.0.0.0:{port}", creds)
        logger.info("grpc_server_mtls", port=port)
    else:
        server.add_insecure_port(f"0.0.0.0:{port}")
        logger.warning("grpc_server_insecure", port=port)

    server.start()
    logger.info("grpc_server_started", port=port)
    server.wait_for_termination()


if __name__ == "__main__":
    from loguru import logger as _log
    _log.add("/opt/agentbox/logs/grpc-server.log", rotation="50 MB")
    serve()
