from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import ActivityLog, User
from ..schemas import ActivityLogOut


router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("", response_model=list[ActivityLogOut])
def list_activity(
    level: str | None = None,
    limit: int = Query(default=100, ge=1, le=300),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ActivityLog]:
    query = db.query(ActivityLog).filter(ActivityLog.organization_id == user.organization_id)
    if level and level != "all":
        query = query.filter(ActivityLog.level == level)
    return query.order_by(desc(ActivityLog.created_at)).limit(limit).all()

