from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..adapters.crm import sync_conversation_to_crm
from ..adapters.llm import get_llm
from ..adapters.llm.base import RetrievedContext
from ..adapters.llm.mock import MockLLMAdapter
from ..models import (
    CRMRecord,
    Conversation,
    DraftSource,
    Message,
    ResponseDraft,
    WebhookDelivery,
    utcnow,
)
from ..schemas import PublicInquiryCreate
from .audit import log_activity
from .rag import search_knowledge
from .webhooks import dispatch_conversation_webhook


@dataclass
class SendOutcome:
    conversation: Conversation
    crm_record: CRMRecord | None
    webhook_delivery: WebhookDelivery | None


def latest_draft(db: Session, conversation: Conversation) -> ResponseDraft | None:
    return (
        db.query(ResponseDraft)
        .filter(
            ResponseDraft.organization_id == conversation.organization_id,
            ResponseDraft.conversation_id == conversation.id,
        )
        .order_by(ResponseDraft.created_at.desc())
        .first()
    )


def generate_draft(
    db: Session,
    *,
    conversation: Conversation,
    user_message: str,
    user_id: str | None = None,
) -> ResponseDraft:
    adapter = get_llm()
    provider_name = adapter.name
    try:
        classification = adapter.classify(conversation.subject, user_message)
    except Exception as exc:
        adapter = MockLLMAdapter()
        provider_name = "mock-fallback"
        classification = adapter.classify(conversation.subject, user_message)
        log_activity(
            db,
            organization_id=conversation.organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            action="ai.classification_failed",
            entity_type="conversation",
            entity_id=conversation.id,
            level="error",
            details={"error": str(exc)},
            is_demo=conversation.is_demo,
        )
    conversation.category = classification.category
    conversation.intent = classification.intent
    conversation.urgency = classification.urgency
    hits = search_knowledge(
        db,
        organization_id=conversation.organization_id,
        query=f"{conversation.subject}\n{user_message}",
    )
    contexts = [
        RetrievedContext(
            rank=hit.rank,
            title=hit.title,
            content=hit.content,
            score=hit.score,
        )
        for hit in hits
    ]
    try:
        generated = adapter.draft(conversation.subject, user_message, contexts)
    except Exception as exc:
        generated = MockLLMAdapter().draft(conversation.subject, user_message, contexts)
        provider_name = "mock-fallback"
        log_activity(
            db,
            organization_id=conversation.organization_id,
            user_id=user_id,
            conversation_id=conversation.id,
            action="ai.draft_failed",
            entity_type="conversation",
            entity_id=conversation.id,
            level="error",
            details={"error": str(exc)},
            is_demo=conversation.is_demo,
        )
    draft = ResponseDraft(
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
        body=generated.body,
        confidence=generated.confidence,
        provider=provider_name,
        status="draft",
        is_demo=conversation.is_demo,
    )
    db.add(draft)
    db.flush()
    for hit in hits:
        db.add(
            DraftSource(
                organization_id=conversation.organization_id,
                draft_id=draft.id,
                source_id=hit.source_id,
                chunk_id=hit.chunk_id,
                rank=hit.rank,
                score=hit.score,
                quote=hit.content[:700],
                is_demo=conversation.is_demo,
            )
        )
    log_activity(
        db,
        organization_id=conversation.organization_id,
        user_id=user_id,
        conversation_id=conversation.id,
        action="ai.draft_created",
        entity_type="response_draft",
        entity_id=draft.id,
        details={
            "provider": provider_name,
            "confidence": generated.confidence,
            "sources": len(hits),
            "category": classification.category,
            "intent": classification.intent,
            "urgency": classification.urgency,
        },
        is_demo=conversation.is_demo,
    )
    db.flush()
    return draft


def create_public_inquiry(
    db: Session, *, organization_id: str, payload: PublicInquiryCreate
) -> Conversation:
    conversation = Conversation(
        organization_id=organization_id,
        customer_name=payload.name,
        customer_email=str(payload.email).lower(),
        customer_company=payload.company,
        subject=payload.subject,
        status="needs_review",
    )
    db.add(conversation)
    db.flush()
    message = Message(
        organization_id=organization_id,
        conversation_id=conversation.id,
        role="customer",
        body=payload.message,
        status="received",
    )
    db.add(message)
    log_activity(
        db,
        organization_id=organization_id,
        conversation_id=conversation.id,
        action="conversation.received",
        entity_type="conversation",
        entity_id=conversation.id,
        details={"channel": "public_form", "reference": conversation.public_reference},
    )
    generate_draft(db, conversation=conversation, user_message=payload.message)
    db.commit()
    db.refresh(conversation)
    return conversation


def edit_draft(
    db: Session, *, conversation: Conversation, body: str, user_id: str
) -> ResponseDraft:
    draft = latest_draft(db, conversation)
    if draft is None or draft.status == "sent":
        raise ValueError("There is no editable draft for this conversation.")
    draft.body = body
    draft.status = "draft"
    draft.edited_by_id = user_id
    draft.approved_by_id = None
    draft.approved_at = None
    log_activity(
        db,
        organization_id=conversation.organization_id,
        user_id=user_id,
        conversation_id=conversation.id,
        action="draft.edited",
        entity_type="response_draft",
        entity_id=draft.id,
        details={"characters": len(body)},
        is_demo=conversation.is_demo,
    )
    db.commit()
    db.refresh(draft)
    return draft


def approve_draft(
    db: Session, *, conversation: Conversation, user_id: str
) -> ResponseDraft:
    draft = latest_draft(db, conversation)
    if draft is None or draft.status == "sent":
        raise ValueError("There is no draft to approve.")
    draft.status = "approved"
    draft.approved_by_id = user_id
    draft.approved_at = utcnow()
    conversation.status = "approved"
    log_activity(
        db,
        organization_id=conversation.organization_id,
        user_id=user_id,
        conversation_id=conversation.id,
        action="draft.approved",
        entity_type="response_draft",
        entity_id=draft.id,
        details={"confidence": draft.confidence},
        is_demo=conversation.is_demo,
    )
    db.commit()
    db.refresh(draft)
    return draft


def send_approved_draft(
    db: Session, *, conversation: Conversation, user_id: str
) -> SendOutcome:
    draft = latest_draft(db, conversation)
    if draft is None or draft.status != "approved":
        raise PermissionError("Approve the current draft before sending it.")
    message = Message(
        organization_id=conversation.organization_id,
        conversation_id=conversation.id,
        role="employee",
        body=draft.body,
        status="sent",
        created_by_id=user_id,
        is_demo=conversation.is_demo,
    )
    db.add(message)
    draft.status = "sent"
    draft.sent_at = utcnow()
    conversation.status = "sent"
    log_activity(
        db,
        organization_id=conversation.organization_id,
        user_id=user_id,
        conversation_id=conversation.id,
        action="response.sent",
        entity_type="message",
        entity_id=message.id,
        details={"channel": "web", "draft_id": draft.id},
        is_demo=conversation.is_demo,
    )
    crm_record = sync_conversation_to_crm(
        db, conversation=conversation, response_body=draft.body, user_id=user_id
    )
    webhook = dispatch_conversation_webhook(db, conversation=conversation, user_id=user_id)
    db.commit()
    db.refresh(conversation)
    if crm_record:
        db.refresh(crm_record)
    if webhook:
        db.refresh(webhook)
    return SendOutcome(conversation=conversation, crm_record=crm_record, webhook_delivery=webhook)
