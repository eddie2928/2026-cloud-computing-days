import json
import logging
import traceback as tb

from pywebpush import WebPushException, webpush

from app.config import get_settings

logger = logging.getLogger(__name__)

_EXPIRED_STATUS_CODES = {404, 410}


def send_one(endpoint: str, p256dh: str, auth: str, payload: dict) -> dict:
    """Send a push notification to a single subscription.

    Returns a dict with keys: success, expired, error, status_code, traceback.
    """
    settings = get_settings()

    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return {"success": True, "expired": False, "error": None, "status_code": None, "traceback": None}
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        expired = status in _EXPIRED_STATUS_CODES
        error_msg = str(exc)
        trace = tb.format_exc()
        if expired:
            logger.info("Push subscription expired (%s), will delete: %s", status, endpoint)
        else:
            logger.warning("Push send failed (status=%s): %s\n%s", status, exc, trace)
        return {"success": False, "expired": expired, "error": error_msg, "status_code": status, "traceback": trace}
    except Exception as exc:
        error_msg = str(exc)
        trace = tb.format_exc()
        logger.warning("Push send unexpected error: %s\n%s", exc, trace)
        return {"success": False, "expired": False, "error": error_msg, "status_code": None, "traceback": trace}
