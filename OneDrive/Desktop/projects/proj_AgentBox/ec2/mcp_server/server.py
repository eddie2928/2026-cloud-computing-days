"""EC2 MCP Server - list_project_files + decrypt_and_stage (chunked, Zero-Knowledge)."""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import boto3
import uvicorn
from fastapi import FastAPI, HTTPException, Security
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_PROJECT = os.environ.get("PROJECT_NAME", "agentbox")
_ENCRYPTED_CODE_BUCKET = f"{_PROJECT}-encrypted-code"
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

_s3 = boto3.client("s3", region_name=_REGION)
_security = HTTPBearer()

_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".tar",
    ".gz", ".exe", ".dll", ".so", ".dylib", ".bin", ".mp3", ".mp4",
    ".mov", ".wav",
}


def _verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)) -> str:
    if _ADMIN_TOKEN and credentials.credentials != _ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


def _is_binary_bytes(data: bytes) -> bool:
    """Heuristic: NUL byte present, or <70% ASCII-printable in first 8KB."""
    sample = data[:8192]
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    ascii_count = sum(
        1 for b in sample
        if b in (0x09, 0x0A, 0x0D) or 0x20 <= b <= 0x7E
    )
    return (ascii_count / len(sample)) < 0.70


app = FastAPI(title="AgentBox MCP Server")


class DecryptRequest(BaseModel):
    project_id: str
    files: list[str]
    start_byte: int = 0
    max_bytes: int = 20480


class FileChunk(BaseModel):
    path: str
    is_binary: bool
    size: int
    returned_bytes: int
    next_offset: Optional[int]
    truncated: bool
    content: Optional[str]
    error: Optional[str]


class DecryptResponse(BaseModel):
    project_id: str
    files: list[FileChunk]


@app.get("/mcp/list_files/{project_id}")
async def list_project_files(project_id: str, token: str = Security(_verify_token)):
    """List all encrypted files for a project as a Markdown table."""
    prefix = f"encrypted_code/{project_id}/"
    paginator = _s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=_ENCRYPTED_CODE_BUCKET, Prefix=prefix):
        objects.extend(page.get("Contents", []))

    total_size = sum(o["Size"] for o in objects)
    lines = [
        f"# Project files: {project_id}",
        f"Total: {len(objects)} files, {total_size} bytes encrypted",
        "",
        "| Path | Size (encrypted bytes) | Is Binary | Last Modified (UTC) |",
        "|---|---|---|---|",
    ]
    for obj in objects:
        key = obj["Key"]
        rel = key[len(prefix):]
        if rel.endswith(".enc"):
            rel = rel[:-4]
        ext = Path(rel).suffix.lower()
        is_bin = ext in _BINARY_EXTENSIONS
        mod = obj["LastModified"].strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(f"| {rel} | {obj['Size']} | {'true' if is_bin else 'false'} | {mod} |")

    body = "\n".join(lines)
    logger.info("list_files_done", project_id=project_id, count=len(objects), response_bytes=len(body))
    return Response(content=body, media_type="text/markdown; charset=utf-8")


@app.post("/mcp/decrypt_and_stage", response_model=DecryptResponse)
async def decrypt_and_stage(req: DecryptRequest, token: str = Security(_verify_token)):
    """Decrypt specified files, return plaintext content inline (Zero-Knowledge: no S3 staging)."""
    if not req.files:
        raise HTTPException(status_code=422, detail="files list must not be empty")

    project_id = req.project_id
    chunks: list[FileChunk] = []

    for rel_path in req.files:
        # Security: reject directory traversal
        try:
            parts = Path(rel_path).parts
            if ".." in parts or Path(rel_path).is_absolute():
                chunks.append(FileChunk(
                    path=rel_path, is_binary=False, size=0, returned_bytes=0,
                    next_offset=None, truncated=False, content=None,
                    error="invalid_path: directory traversal not allowed",
                ))
                continue
        except Exception:
            chunks.append(FileChunk(
                path=rel_path, is_binary=False, size=0, returned_bytes=0,
                next_offset=None, truncated=False, content=None,
                error="invalid_path",
            ))
            continue

        s3_key = f"encrypted_code/{project_id}/{rel_path}.enc"
        enc_path = None
        buf = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as tmp:
                try:
                    _s3.download_fileobj(_ENCRYPTED_CODE_BUCKET, s3_key, tmp)
                except Exception:
                    chunks.append(FileChunk(
                        path=rel_path, is_binary=False, size=0, returned_bytes=0,
                        next_offset=None, truncated=False, content=None,
                        error="not_found",
                    ))
                    continue
                enc_path = tmp.name

            result = subprocess.run(
                ["sops", "--decrypt", "--input-type", "binary", "--output-type", "binary", enc_path],
                capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                err_msg = result.stderr.decode()[:80]
                chunks.append(FileChunk(
                    path=rel_path, is_binary=False, size=0, returned_bytes=0,
                    next_offset=None, truncated=False, content=None,
                    error=f"decrypt_failed: {err_msg}",
                ))
                continue

            buf = bytearray(result.stdout)
            is_bin = _is_binary_bytes(bytes(buf))

            if is_bin:
                chunks.append(FileChunk(
                    path=rel_path, is_binary=True, size=len(buf), returned_bytes=0,
                    next_offset=None, truncated=False, content=None, error=None,
                ))
            else:
                chunk = bytes(buf)[req.start_byte: req.start_byte + req.max_bytes]
                try:
                    content = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    content = chunk.decode("utf-8", errors="replace")
                    logger.warning("utf8_decode_replace", path=rel_path)

                returned = len(chunk)
                truncated = (req.start_byte + returned) < len(buf)
                next_off = req.start_byte + returned if truncated else None
                chunks.append(FileChunk(
                    path=rel_path, is_binary=False, size=len(buf),
                    returned_bytes=returned, next_offset=next_off,
                    truncated=truncated, content=content, error=None,
                ))
        finally:
            if buf is not None:
                buf[:] = b"\x00" * len(buf)
            if enc_path:
                Path(enc_path).unlink(missing_ok=True)

    resp = DecryptResponse(project_id=project_id, files=chunks)
    resp_json = resp.model_dump_json()
    if len(resp_json.encode()) > 24576:
        logger.warning("response_near_bedrock_limit", bytes=len(resp_json.encode()))
    logger.info("decrypt_done", project_id=project_id, files=len(chunks))
    return resp


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "mcp"}


if __name__ == "__main__":
    from loguru import logger as _log
    _log.add("/opt/agentbox/logs/mcp-server.log", rotation="50 MB")
    port = int(os.environ.get("MCP_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
