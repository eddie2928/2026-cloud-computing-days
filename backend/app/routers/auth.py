from fastapi import APIRouter, HTTPException, Response, status

from app.auth import create_session_cookie, verify_password
from app.config import get_settings
from app.schemas import LoginRequest

router = APIRouter(prefix="/api", tags=["auth"])

_COOKIE_NAME = "session"
_COOKIE_MAX_AGE = 86400 * 7


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    if not verify_password(body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password")
    token = create_session_cookie()
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        secure=get_settings().cookie_secure,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=_COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
async def me():
    return {"user_id": 1}
