import secrets

from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

_DEFAULT_USER_ID = 1
_COOKIE_NAME = "session"
_MAX_AGE_SECONDS = 86400 * 7  # 7 days


def verify_password(input_password: str) -> bool:
    return secrets.compare_digest(input_password, get_settings().app_password)


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret)


def create_session_cookie() -> str:
    return _get_serializer().dumps(_DEFAULT_USER_ID)


def verify_session_cookie(token: str) -> int | None:
    try:
        user_id = _get_serializer().loads(token, max_age=_MAX_AGE_SECONDS)
        return int(user_id)
    except (BadSignature, SignatureExpired):
        return None


async def require_session(session: str | None = Cookie(default=None, alias=_COOKIE_NAME)) -> int:
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = verify_session_cookie(session)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user_id
