from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, WebhookDelivery
from ..schemas import WebhookDeliveryOut
from ..services.webhooks import retry_webhook


router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.get("", response_model=list[WebhookDeliveryOut])
def list_deliveries(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WebhookDelivery]:
    return (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.organization_id == user.organization_id)
        .order_by(desc(WebhookDelivery.created_at))
        .limit(100)
        .all()
    )


@router.post("/{delivery_id}/retry", response_model=WebhookDeliveryOut)
def retry(
    delivery_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookDelivery:
    delivery = (
        db.query(WebhookDelivery)
        .filter(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.organization_id == user.organization_id,
        )
        .one_or_none()
    )
    if delivery is None:
        raise HTTPException(status_code=404, detail="Webhook delivery not found.")
    if delivery.status == "delivered":
        raise HTTPException(status_code=409, detail="This webhook was already delivered.")
    return retry_webhook(db, delivery=delivery, user_id=user.id)

