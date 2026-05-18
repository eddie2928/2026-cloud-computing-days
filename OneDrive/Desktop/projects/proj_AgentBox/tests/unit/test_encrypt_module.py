"""Unit tests for agentbox.encrypt (Task-7 D1 / Tasks.md E1)."""
import io
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws


@pytest.fixture
def sops_yaml(tmp_path):
    sy = tmp_path / "sops.yaml"
    sy.write_text("creation_rules:\n  - kms: arn:aws:kms:us-east-1:123456789012:key/fake-key\n")
    return sy


@pytest.fixture
def src_dir(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a.py", "b.py", "sub/c.py", "sub/d.py"):
        p = src / name
        p.parent.mkdir(exist_ok=True)
        p.write_text(f"# {name}")
    return src


# ── E1: encrypt_local 단위 테스트 ──────────────────────────────────────────────
def test_encrypt_local_creates_enc_files(src_dir, sops_yaml):
    from agentbox.encrypt import encrypt_local
    import shutil

    def fake_sops(cmd, capture_output, cwd, **kw):
        input_file = Path(cmd[-1])
        data = input_file.read_bytes()
        return type("R", (), {"returncode": 0, "stdout": b"ENC:" + data, "stderr": b""})()

    with patch("agentbox.encrypt.subprocess.run", side_effect=fake_sops):
        enc_dir = encrypt_local(src_dir, sops_yaml=sops_yaml)
    try:
        enc_files = list(enc_dir.rglob("*.enc"))
        assert len(enc_files) == 4
    finally:
        shutil.rmtree(enc_dir, ignore_errors=True)


def test_upload_via_ec2_posts_zip(tmp_path, sops_yaml, src_dir):
    from agentbox.encrypt import encrypt_local, upload_via_ec2
    import shutil

    def fake_sops(cmd, capture_output, cwd, **kw):
        return type("R", (), {"returncode": 0, "stdout": b"ENCRYPTED", "stderr": b""})()

    with patch("agentbox.encrypt.subprocess.run", side_effect=fake_sops):
        enc_dir = encrypt_local(src_dir, sops_yaml=sops_yaml)

    try:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch("agentbox.encrypt.requests.post", return_value=mock_resp) as mock_post:
            upload_via_ec2(
                enc_dir, "proj-1",
                "https://ec2.example.com:8443",
                "/tmp/ep.crt", "/tmp/ep.key", "/tmp/ca.crt",
            )
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["cert"] == ("/tmp/ep.crt", "/tmp/ep.key")
        assert call_kwargs["verify"] == "/tmp/ca.crt"
        # Verify the posted file is a valid zip
        posted_buf = mock_post.call_args[1]["files"]["file"][1]
        posted_buf.seek(0)
        assert zipfile.is_zipfile(posted_buf)
    finally:
        shutil.rmtree(enc_dir, ignore_errors=True)


# ── T1: 4개 파일 → SOPS fake CLI + S3 업로드 검증 ─────────────────────────────
@mock_aws
def test_encrypt_and_upload_success(src_dir, sops_yaml):
    import boto3
    from agentbox.encrypt import encrypt_and_upload

    # Create S3 bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "test-bucket"
    s3.create_bucket(Bucket=bucket)

    # Fake sops: echo input bytes back as "encrypted"
    def fake_sops(cmd, capture_output, cwd, **kw):
        input_file = Path(cmd[-1])
        data = input_file.read_bytes()
        mock = type("R", (), {"returncode": 0, "stdout": b"ENC:" + data, "stderr": b""})()
        return mock

    with patch("agentbox.encrypt.subprocess.run", side_effect=fake_sops):
        encrypt_and_upload(src_dir, bucket, "myrepo", sops_yaml=sops_yaml)

    # Verify all 4 files uploaded
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="encrypted_code/myrepo/")
    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert len(keys) == 4
    for key in keys:
        assert key.endswith(".enc")


# ── T2: SOPS non-zero → CalledProcessError 발생 ───────────────────────────────
@mock_aws
def test_sops_failure_raises(src_dir, sops_yaml):
    import boto3
    from agentbox.encrypt import encrypt_and_upload

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    def fake_sops_fail(cmd, capture_output, cwd, **kw):
        return type("R", (), {"returncode": 5, "stdout": b"", "stderr": b"KMS error"})()

    with patch("agentbox.encrypt.subprocess.run", side_effect=fake_sops_fail):
        with pytest.raises(subprocess.CalledProcessError):
            encrypt_and_upload(src_dir, "test-bucket", "proj", sops_yaml=sops_yaml)


# ── T3: KMS 미존재 → botocore ClientError 발생 ────────────────────────────────
@mock_aws
def test_kms_missing_raises(src_dir, sops_yaml):
    import boto3
    from botocore.exceptions import ClientError
    from agentbox.encrypt import encrypt_and_upload

    # Don't create the bucket → S3 PutObject fails with NoSuchBucket
    def fake_sops(cmd, capture_output, cwd, **kw):
        return type("R", (), {"returncode": 0, "stdout": b"ENCRYPTED", "stderr": b""})()

    with patch("agentbox.encrypt.subprocess.run", side_effect=fake_sops):
        with pytest.raises(ClientError):
            # bucket doesn't exist → S3 raises ClientError
            encrypt_and_upload(src_dir, "nonexistent-bucket", "proj", sops_yaml=sops_yaml)
