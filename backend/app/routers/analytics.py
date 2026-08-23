from __future__ import annotations

from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Conversation, ResponseDraft, User, WebhookDelivery, utcnow
from ..schemas import AnalyticsOut


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
def analytics(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AnalyticsOut:
    conversations = (
        db.query(Conversation)
        .filter(Conversation.organization_id == user.organization_id)
        .all()
    )
    status_counts = Counter(item.status for item in conversations)
    category_counts = Counter(item.category for item in conversations)
    average_confidence = (
        db.query(func.avg(ResponseDraft.confidence))
        .filter(ResponseDraft.organization_id == user.organization_id)
        .scalar()
        or 0.0
    )
    webhook_failures = (
        db.query(func.count(WebhookDelivery.id))
        .filter(
            WebhookDelivery.organization_id == user.organization_id,
            WebhookDelivery.status == "failed",
        )
        .scalar()
        or 0
    )
    today = utcnow().date()
    daily = Counter(item.created_at.date() for item in conversations)
    seven_days = [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "count": daily[today - timedelta(days=offset)],
        }
        for offset in reversed(range(7))
    ]
    return AnalyticsOut(
        total_conversations=len(conversations),
        needs_review=status_counts["needs_review"],
        sent=status_counts["sent"],
        escalated=status_counts["escalated"],
        average_confidence=round(float(average_confidence), 3),
        webhook_failures=int(webhook_failures),
        by_category=dict(category_counts),
        last_seven_days=seven_days,
    )

