from __future__ import annotations

from sqlalchemy.orm import Session

from .auth import hash_password
from .models import (
    Conversation,
    CRMRecord,
    DraftSource,
    Integration,
    Message,
    Organization,
    ResponseDraft,
    User,
    WebhookDelivery,
    utcnow,
)
from .schemas import PublicInquiryCreate
from .services.audit import log_activity
from .services.conversations import create_public_inquiry
from .services.knowledge import create_and_index_source


DEMO_SLUG = "demo-leadops"
DEMO_ADMIN_EMAIL = "admin@demo.leadops.ai"
DEMO_EMPLOYEE_EMAIL = "agent@demo.leadops.ai"
DEMO_PASSWORD = "DemoLeadOps2026!"


def _mark_conversation_demo(db: Session, conversation: Conversation) -> None:
    conversation.is_demo = True
    for message in conversation.messages:
        message.is_demo = True
    for draft in conversation.drafts:
        draft.is_demo = True
        for source in draft.sources:
            source.is_demo = True
    db.flush()


def seed_demo(db: Session) -> None:
    if db.query(Organization).filter(Organization.slug == DEMO_SLUG).first():
        return
    organization = Organization(
        name="Northstar Components (demo)", slug=DEMO_SLUG, is_demo=True
    )
    db.add(organization)
    db.flush()
    admin = User(
        organization_id=organization.id,
        email=DEMO_ADMIN_EMAIL,
        full_name="Maya Chen (demo)",
        password_hash=hash_password(DEMO_PASSWORD),
        role="admin",
        is_demo=True,
    )
    employee = User(
        organization_id=organization.id,
        email=DEMO_EMPLOYEE_EMAIL,
        full_name="Noah Williams (demo)",
        password_hash=hash_password(DEMO_PASSWORD),
        role="employee",
        is_demo=True,
    )
    db.add_all([admin, employee])
    db.flush()
    db.add(
        Integration(
            organization_id=organization.id,
            kind="crm",
            provider="test",
            enabled=True,
            config={"create_object": "ticket"},
            last_test_status="connected",
            is_demo=True,
        )
    )
    db.add(
        Integration(
            organization_id=organization.id,
            kind="workflow",
            provider="n8n",
            enabled=False,
            config={"webhook_url": "http://n8n:5678/webhook/leadops-demo"},
            is_demo=True,
        )
    )
    db.commit()

    create_and_index_source(
        db,
        organization_id=organization.id,
        created_by_id=admin.id,
        kind="text",
        title="Northstar service guide (demo)",
        text=(
            "Northstar Components offers Standard and Priority support. Standard support replies "
            "within one business day. Priority support replies within two business hours. "
            "Customers can request a replacement for a damaged controller within 30 days of delivery. "
            "The request must include the order number and a photo of the damaged unit. "
            "Orders above 50 units qualify for volume pricing. A sales specialist prepares the quote "
            "after receiving the required quantity, destination country, and requested delivery date. "
            "The NX-24 controller supports 24 volt industrial systems and has a two-year warranty."
        ),
        mime_type="text/plain",
        is_demo=True,
    )

    first = create_public_inquiry(
        db,
        organization_id=organization.id,
        payload=PublicInquiryCreate(
            name="Elena Ortiz (demo)",
            email="elena@example.demo",
            company="Ortiz Automation (demo)",
            subject="Volume price for 80 NX-24 controllers",
            message=(
                "We need 80 NX-24 controllers delivered to Spain next month. "
                "Can you tell me how volume pricing works?"
            ),
        ),
    )
    first.assigned_to_id = employee.id
    _mark_conversation_demo(db, first)

    second = create_public_inquiry(
        db,
        organization_id=organization.id,
        payload=PublicInquiryCreate(
            name="Samir Patel (demo)",
            email="samir@example.demo",
            company="Patel Systems (demo)",
            subject="Damaged controller, line is stopped",
            message=(
                "One controller arrived damaged and our line is stopped. This is urgent. "
                "What do you need from us for a replacement?"
            ),
        ),
    )
    second.status = "escalated"
    second.assigned_to_id = admin.id
    _mark_conversation_demo(db, second)
    db.add(
        Message(
            organization_id=organization.id,
            conversation_id=second.id,
            role="internal",
            body="Demo note: escalated because production is stopped.",
            status="note",
            created_by_id=employee.id,
            is_demo=True,
        )
    )

    third = create_public_inquiry(
        db,
        organization_id=organization.id,
        payload=PublicInquiryCreate(
            name="Jo Reed (demo)",
            email="jo@example.demo",
            company="Reed Controls (demo)",
            subject="Priority support response time",
            message="What response time is included in Priority support?",
        ),
    )
    _mark_conversation_demo(db, third)
    latest = max(third.drafts, key=lambda item: item.created_at)
    latest.status = "sent"
    latest.approved_by_id = admin.id
    latest.approved_at = utcnow()
    latest.sent_at = utcnow()
    third.status = "sent"
    third.assigned_to_id = admin.id
    db.add(
        Message(
            organization_id=organization.id,
            conversation_id=third.id,
            role="employee",
            body=latest.body,
            status="sent",
            created_by_id=admin.id,
            is_demo=True,
        )
    )
    crm_record = CRMRecord(
        organization_id=organization.id,
        conversation_id=third.id,
        provider="test",
        object_type="ticket",
        external_id=f"demo_{third.id[:12]}",
        payload={"demo": True, "status": "new"},
        is_demo=True,
    )
    db.add(crm_record)
    db.flush()
    log_activity(
        db,
        organization_id=organization.id,
        user_id=admin.id,
        conversation_id=third.id,
        action="crm.synced",
        entity_type="crm_record",
        entity_id=crm_record.id,
        details={
            "provider": "test",
            "object_type": "ticket",
            "external_id": crm_record.external_id,
        },
        is_demo=True,
    )
    webhook = WebhookDelivery(
        organization_id=organization.id,
        conversation_id=third.id,
        event="conversation.sent",
        target_url="http://n8n:5678/webhook/leadops-demo",
        payload={
            "event": "conversation.sent",
            "organization_id": organization.id,
            "conversation": {
                "id": third.id,
                "reference": third.public_reference,
                "subject": third.subject,
                "status": third.status,
            },
        },
        status="failed",
        attempt_count=1,
        last_error="Demo delivery: connect n8n to retry this webhook.",
        last_attempt_at=utcnow(),
        is_demo=True,
    )
    db.add(webhook)
    db.flush()
    log_activity(
        db,
        organization_id=organization.id,
        user_id=admin.id,
        conversation_id=third.id,
        action="webhook.failed",
        entity_type="webhook_delivery",
        entity_id=webhook.id,
        level="error",
        details={
            "target_url": webhook.target_url,
            "status": webhook.status,
            "attempt": webhook.attempt_count,
            "error": webhook.last_error,
        },
        is_demo=True,
    )
    log_activity(
        db,
        organization_id=organization.id,
        user_id=admin.id,
        conversation_id=third.id,
        action="response.sent",
        entity_type="conversation",
        entity_id=third.id,
        details={"demo": True, "channel": "web"},
        is_demo=True,
    )
    db.commit()
