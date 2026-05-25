import base64
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

_FAKE_PEM = b"-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----\n"
os.environ.setdefault("APP_PASSWORD", "inha-nxt")
os.environ.setdefault("SESSION_SECRET", "test-secret-key-for-session-signing-32ch")
os.environ.setdefault("DB_URL", "postgresql+asyncpg://u:p@h/d")
os.environ.setdefault("VAPID_PUBLIC_KEY", "BFakePublicKey87chars" + "x" * 67)
os.environ.setdefault("VAPID_PRIVATE_KEY", base64.b64encode(_FAKE_PEM).decode())
os.environ.setdefault("VAPID_SUBJECT", "mailto:test@example.com")

from app.scheduler import _kst_hhmm, _run_notification_job


def test_kst_hhmm_converts_utc_to_kst():
    # UTC 00:00 = KST 09:00
    with freeze_time("2026-05-25 00:00:00", tz_offset=0):
        hhmm, key = _kst_hhmm()
    assert hhmm == "09:00"
    assert key == "2026-05-25 09:00"


def test_kst_hhmm_midnight_kst():
    # UTC 15:00 = KST 00:00
    with freeze_time("2026-05-25 15:00:00", tz_offset=0):
        hhmm, key = _kst_hhmm()
    assert hhmm == "00:00"


@pytest.mark.asyncio
async def test_run_notification_job_only_sends_to_matching_users():
    """Users with notification_time == current KST HH:MM get push; others don't."""
    session_factory = MagicMock()
    mock_session = AsyncMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    # _get_matching_profiles returns user_id=1 only
    with patch("app.scheduler._get_matching_profiles", new=AsyncMock(return_value=[1])):
        with patch("app.scheduler._get_user_subscriptions", new=AsyncMock(return_value=[])):
            with patch("app.scheduler.send_one", return_value={"success": True, "expired": False, "error": None, "status_code": None, "traceback": None}) as mock_send:
                with freeze_time("2026-05-25 00:00:00", tz_offset=0):  # KST 09:00
                    await _run_notification_job(session_factory)

    # No subscriptions returned, so send_one not called
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_run_notification_job_deduplication():
    """Same user should not be sent twice in the same minute."""
    from app.scheduler import _sent_tracker

    _sent_tracker.clear()
    session_factory = MagicMock()
    mock_session = AsyncMock()
    session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    fake_sub = MagicMock()
    fake_sub.id = 1
    fake_sub.endpoint = "https://fcm.test/1"
    fake_sub.p256dh = "p256"
    fake_sub.auth = "auth"

    with patch("app.scheduler._get_matching_profiles", new=AsyncMock(return_value=[1])):
        with patch("app.scheduler._get_user_subscriptions", new=AsyncMock(return_value=[fake_sub])):
            with patch("app.scheduler.send_one", return_value={"success": True, "expired": False, "error": None, "status_code": None, "traceback": None}) as mock_send:
                with freeze_time("2026-05-25 00:00:00", tz_offset=0):
                    await _run_notification_job(session_factory)
                    call_count_first = mock_send.call_count

                    # Second call in same minute — should be deduplicated
                    await _run_notification_job(session_factory)
                    call_count_second = mock_send.call_count

    assert call_count_first == 1
    assert call_count_second == 1  # no additional calls
    _sent_tracker.clear()
