from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import ActivityLog


def log_activity(
    db: Session,
    *,
    organization_id: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    user_id: str | None = None,
    conversation_id: str | None = None,
    level: str = "info",
    details: dict[str, Any] | None = None,
    is_demo: bool = False,
) -> ActivityLog:
    entry = ActivityLog(
        organization_id=organization_id,
        user_id=user_id,
        conversation_id=conversation_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        level=level,
        details=details or {},
        is_demo=is_demo,
    )
    db.add(entry)
    return entry

