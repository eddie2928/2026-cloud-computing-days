"""Unit tests for agentbox.encrypt (Task-7 D1)."""
import subprocess
from pathlib import Path
from unittest.mock import patch

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
