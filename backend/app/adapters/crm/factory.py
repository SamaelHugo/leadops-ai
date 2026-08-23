from __future__ import annotations

from sqlalchemy.orm import Session

from ...auth import decrypt_secret
from ...models import CRMRecord, Conversation, Integration
from ...services.audit import log_activity
from .base import CRMAdapter


def _adapter(integration: Integration) -> CRMAdapter:
    if integration.provider == "hubspot":
        token = decrypt_secret(integration.encrypted_secret)
        if not token:
            raise RuntimeError("HubSpot access token is missing")
        from .hubspot import HubSpotAdapter

        return HubSpotAdapter(token, integration.config or {})
    from .test import TestCRMAdapter

    return TestCRMAdapter()


def test_crm_connection(integration: Integration) -> None:
    _adapter(integration).test_connection()


def sync_conversation_to_crm(
    db: Session, *, conversation: Conversation, response_body: str, user_id: str
) -> CRMRecord | None:
    integration = (
        db.query(Integration)
        .filter(
            Integration.organization_id == conversation.organization_id,
            Integration.kind == "crm",
            Integration.enabled.is_(True),
        )
        .one_or_none()
    )
    if integration is None:
        return None
    try:
        result = _adapter(integration).upsert(conversation, response_body)
        record = (
            db.query(CRMRecord)
            .filter(
                CRMRecord.organization_id == conversation.organization_id,
                CRMRecord.conversation_id == conversation.id,
                CRMRecord.provider == result.provider,
            )
            .one_or_none()
        )
        if record is None:
            record = CRMRecord(
                organization_id=conversation.organization_id,
                conversation_id=conversation.id,
                provider=result.provider,
                object_type=result.object_type,
                external_id=result.external_id,
                payload=result.payload,
                is_demo=conversation.is_demo or result.provider == "test",
            )
            db.add(record)
        else:
            record.object_type = result.object_type
            record.external_id = result.external_id
            record.payload = result.payload
        log_activity(
            db,
            organization_id=conversation.organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            action="crm.synced",
            entity_type="crm_record",
            entity_id=record.id,
            details={
                "provider": result.provider,
                "object_type": result.object_type,
                "external_id": result.external_id,
            },
            is_demo=record.is_demo,
        )
        db.flush()
        return record
    except Exception as exc:
        log_activity(
            db,
            organization_id=conversation.organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            action="crm.failed",
            entity_type="integration",
            entity_id=integration.id,
            level="error",
            details={"provider": integration.provider, "error": str(exc)},
            is_demo=conversation.is_demo,
        )
        db.flush()
        return None

