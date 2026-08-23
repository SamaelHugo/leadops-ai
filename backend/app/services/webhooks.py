from __future__ import annotations

import hashlib
import hmac
import json

import httpx
from sqlalchemy.orm import Session

from ..auth import decrypt_secret
from ..config import get_settings
from ..models import Conversation, Integration, WebhookDelivery, utcnow
from .audit import log_activity


def _signature(payload: dict, secret: str | None) -> str | None:
    if not secret:
        return None
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(secret.encode(), encoded, hashlib.sha256).hexdigest()


def _attempt(db: Session, delivery: WebhookDelivery, secret: str | None) -> WebhookDelivery:
    delivery.attempt_count += 1
    delivery.last_attempt_at = utcnow()
    headers = {"Content-Type": "application/json", "X-LeadOps-Event": delivery.event}
    signature = _signature(delivery.payload, secret)
    if signature:
        headers["X-LeadOps-Signature"] = f"sha256={signature}"
    try:
        response = httpx.post(
            delivery.target_url,
            json=delivery.payload,
            headers=headers,
            timeout=get_settings().webhook_timeout_seconds,
        )
        delivery.response_status = response.status_code
        delivery.response_body = response.text[:2_000]
        response.raise_for_status()
        delivery.status = "delivered"
        delivery.last_error = None
        delivery.delivered_at = utcnow()
    except Exception as exc:
        delivery.status = "failed"
        delivery.last_error = str(exc)[:2_000]
    db.flush()
    return delivery


def dispatch_conversation_webhook(
    db: Session, *, conversation: Conversation, user_id: str
) -> WebhookDelivery | None:
    integration = (
        db.query(Integration)
        .filter(
            Integration.organization_id == conversation.organization_id,
            Integration.kind == "workflow",
            Integration.provider == "n8n",
            Integration.enabled.is_(True),
        )
        .one_or_none()
    )
    if integration is None:
        return None
    target_url = str((integration.config or {}).get("webhook_url") or "")
    if not target_url:
        return None
    payload = {
        "event": "conversation.sent",
        "organization_id": conversation.organization_id,
        "conversation": {
            "id": conversation.id,
            "reference": conversation.public_reference,
            "customer_name": conversation.customer_name,
            "customer_email": conversation.customer_email,
            "company": conversation.customer_company,
            "subject": conversation.subject,
            "category": conversation.category,
            "intent": conversation.intent,
            "urgency": conversation.urgency,
            "status": conversation.status,
        },
    }
    delivery = WebhookDelivery(
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
        event="conversation.sent",
        target_url=target_url,
        payload=payload,
        is_demo=conversation.is_demo,
    )
    db.add(delivery)
    db.flush()
    secret = decrypt_secret(integration.encrypted_secret)
    _attempt(db, delivery, secret)
    log_activity(
        db,
        organization_id=conversation.organization_id,
        user_id=user_id,
        conversation_id=conversation.id,
        action=("webhook.delivered" if delivery.status == "delivered" else "webhook.failed"),
        entity_type="webhook_delivery",
        entity_id=delivery.id,
        level="info" if delivery.status == "delivered" else "error",
        details={
            "target_url": target_url,
            "status": delivery.status,
            "attempt": delivery.attempt_count,
            "error": delivery.last_error,
        },
        is_demo=delivery.is_demo,
    )
    return delivery


def retry_webhook(
    db: Session, *, delivery: WebhookDelivery, user_id: str
) -> WebhookDelivery:
    integration = (
        db.query(Integration)
        .filter(
            Integration.organization_id == delivery.organization_id,
            Integration.kind == "workflow",
            Integration.provider == "n8n",
        )
        .one_or_none()
    )
    secret = decrypt_secret(integration.encrypted_secret) if integration else None
    _attempt(db, delivery, secret)
    log_activity(
        db,
        organization_id=delivery.organization_id,
        user_id=user_id,
        conversation_id=delivery.conversation_id,
        action=("webhook.delivered" if delivery.status == "delivered" else "webhook.failed"),
        entity_type="webhook_delivery",
        entity_id=delivery.id,
        level="info" if delivery.status == "delivered" else "error",
        details={
            "retry": True,
            "status": delivery.status,
            "attempt": delivery.attempt_count,
            "error": delivery.last_error,
        },
        is_demo=delivery.is_demo,
    )
    db.commit()
    db.refresh(delivery)
    return delivery

