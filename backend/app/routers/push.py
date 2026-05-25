import sys

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_session
from app.config import get_settings
from app.db import get_db
from app.models import PushSubscription
from app.push import send_one
from app.schemas import PushPublicKeyOut, PushSubscriptionIn

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/public-key", response_model=PushPublicKeyOut)
async def get_public_key():
    return PushPublicKeyOut(public_key=get_settings().vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: PushSubscriptionIn,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
        existing.user_id = user_id
    else:
        db.add(
            PushSubscription(
                user_id=user_id,
                endpoint=body.endpoint,
                p256dh=body.keys.p256dh,
                auth=body.keys.auth,
            )
        )

    await db.commit()
    return {"status": "ok"}


@router.delete("/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    body: PushSubscriptionIn,
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint,
            PushSubscription.user_id == user_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    await db.commit()


@router.post("/test")
async def test_push(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subscriptions = result.scalars().all()

    results = []
    to_delete = []
    for sub in subscriptions:
        result = send_one(
            sub.endpoint,
            sub.p256dh,
            sub.auth,
            {"title": "Days Test", "body": "테스트 푸시입니다 🔔"},
        )
        results.append({
            "endpoint": sub.endpoint,
            "success": result["success"],
            "expired": result["expired"],
            "error": result["error"],
            "status_code": result["status_code"],
            "traceback": result["traceback"],
        })
        if result["expired"]:
            to_delete.append(sub.id)

    if to_delete:
        await db.execute(
            delete(PushSubscription).where(PushSubscription.id.in_(to_delete))
        )
        await db.commit()

    return {"results": results}


@router.get("/debug")
async def debug_push(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    try:
        import pywebpush
        pywebpush_version = pywebpush.__version__
    except Exception:
        pywebpush_version = "unknown"

    private_key = settings.vapid_private_key or ""
    public_key = settings.vapid_public_key or ""

    total_subs = await db.scalar(select(func.count()).select_from(PushSubscription))

    return {
        "vapid_public_key_present": bool(public_key),
        "vapid_public_key_length": len(public_key),
        "vapid_private_key_present": bool(private_key),
        "vapid_private_key_length": len(private_key),
        "vapid_private_key_hint": "raw_base64url" if len(private_key) == 43 else "other",
        "vapid_subject": settings.vapid_subject,
        "pywebpush_version": pywebpush_version,
        "python_version": sys.version,
        "total_subscriptions": total_subs,
    }


@router.get("/subscriptions")
async def list_subscriptions(
    user_id: int = Depends(require_session),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )
    subscriptions = result.scalars().all()

    return [
        {
            "id": sub.id,
            "endpoint": sub.endpoint,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        }
        for sub in subscriptions
    ]
