import base64
import json
import logging

from pywebpush import WebPushException, webpush

from app.config import get_settings

logger = logging.getLogger(__name__)

_EXPIRED_STATUS_CODES = {404, 410}


def send_one(endpoint: str, p256dh: str, auth: str, payload: dict) -> bool:
    """Send a push notification to a single subscription.

    Returns True if the subscription should be deleted (endpoint expired/gone).
    """
    settings = get_settings()
    private_key_pem = base64.b64decode(settings.vapid_private_key).decode()

    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=json.dumps(payload),
            vapid_private_key=private_key_pem,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return False
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in _EXPIRED_STATUS_CODES:
            logger.info("Push subscription expired (%s), will delete: %s", status, endpoint)
            return True
        logger.warning("Push send failed (status=%s): %s", status, exc)
        return False
    except Exception as exc:
        logger.warning("Push send unexpected error: %s", exc)
        return False
