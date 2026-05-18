import os

import pytest

os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")

from app.auth import create_session_cookie, verify_password, verify_session_cookie


def test_verify_correct_password():
    assert verify_password("inha-nxt") is True


def test_verify_wrong_password():
    assert verify_password("wrong") is False


def test_cookie_roundtrip():
    token = create_session_cookie()
    user_id = verify_session_cookie(token)
    assert user_id == 1


def test_cookie_tampered():
    token = create_session_cookie()
    tampered = token[:-1] + ("X" if token[-1] != "X" else "Y")
    result = verify_session_cookie(tampered)
    assert result is None


def test_cookie_expired():
    from unittest.mock import patch
    import time

    token = create_session_cookie()
    with patch("app.auth._MAX_AGE_SECONDS", -1):
        result = verify_session_cookie(token)
    assert result is None
