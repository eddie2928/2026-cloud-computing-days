"""Unit tests for ec2/upload_proxy/server.py using FastAPI TestClient."""
import io
import zipfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ec2.upload_proxy.server import app

client = TestClient(app)


def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_verify_cert():
    resp = client.get("/verify_cert")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cert_ok"


def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_upload_returns_project_id_and_file_count():
    zip_bytes = _make_zip({"a.txt": b"hello", "b.txt": b"world"})
    with patch("ec2.upload_proxy.server._encrypt_and_store"):
        resp = client.post(
            "/upload",
            data={"project_id": "proj-123"},
            files={"file": ("project.zip", zip_bytes, "application/zip")},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == "proj-123"
    assert body["files"] == 2


def test_upload_rejects_non_zip():
    with patch("ec2.upload_proxy.server._encrypt_and_store"):
        resp = client.post(
            "/upload",
            data={"project_id": "proj-abc"},
            files={"file": ("bad.zip", b"not a zip", "application/zip")},
        )
    assert resp.status_code == 400
