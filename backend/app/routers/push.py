from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
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
    for sub in subscriptions:
        expired = send_one(
            sub.endpoint,
            sub.p256dh,
            sub.auth,
            {"title": "Days Test", "body": "테스트 푸시입니다 🔔"},
        )
        results.append({"endpoint": sub.endpoint, "success": not expired, "expired": expired})

    return {"results": results}


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
