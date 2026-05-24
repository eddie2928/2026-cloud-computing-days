import base64
import os
from unittest.mock import MagicMock, patch

import pytest

# Minimal env so settings load without a real .env
_FAKE_PEM = b"-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n"
os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")
os.environ.setdefault("VAPID_PUBLIC_KEY", "BFakePublicKey87chars" + "x" * 67)
os.environ.setdefault("VAPID_PRIVATE_KEY", base64.b64encode(_FAKE_PEM).decode())
os.environ.setdefault("VAPID_SUBJECT", "mailto:test@example.com")

from app.push import send_one


@patch("app.push.webpush")
def test_send_one_success(mock_webpush):
    mock_webpush.return_value = MagicMock(status_code=201)

    should_delete = send_one(
        endpoint="https://fcm.googleapis.com/test",
        p256dh="p256dh_value",
        auth="auth_value",
        payload={"title": "Test", "body": "Hello"},
    )

    assert should_delete is False
    mock_webpush.assert_called_once()
    call_kwargs = mock_webpush.call_args.kwargs
    assert call_kwargs["subscription_info"]["endpoint"] == "https://fcm.googleapis.com/test"
    assert call_kwargs["subscription_info"]["keys"]["p256dh"] == "p256dh_value"
    assert call_kwargs["subscription_info"]["keys"]["auth"] == "auth_value"


@pytest.mark.parametrize("status_code", [410, 404])
@patch("app.push.webpush")
def test_send_one_expired_subscription(mock_webpush, status_code):
    from pywebpush import WebPushException

    fake_response = MagicMock(status_code=status_code)
    mock_webpush.side_effect = WebPushException("Gone", response=fake_response)

    should_delete = send_one(
        endpoint="https://fcm.googleapis.com/expired",
        p256dh="p256dh",
        auth="auth",
        payload={"title": "T", "body": "B"},
    )

    assert should_delete is True


@patch("app.push.webpush")
def test_send_one_other_error_no_delete(mock_webpush):
    from pywebpush import WebPushException

    fake_response = MagicMock(status_code=500)
    mock_webpush.side_effect = WebPushException("Server Error", response=fake_response)

    should_delete = send_one(
        endpoint="https://fcm.googleapis.com/test",
        p256dh="p256dh",
        auth="auth",
        payload={"title": "T", "body": "B"},
    )

    assert should_delete is False
