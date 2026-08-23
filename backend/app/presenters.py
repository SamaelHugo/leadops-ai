from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Conversation, DraftSource, ResponseDraft
from .schemas import (
    ConversationDetailOut,
    DraftOut,
    DraftSourceOut,
    MessageOut,
)


def present_draft(db: Session, draft: ResponseDraft | None) -> DraftOut | None:
    if draft is None:
        return None
    sources = (
        db.query(DraftSource)
        .filter(
            DraftSource.organization_id == draft.organization_id,
            DraftSource.draft_id == draft.id,
        )
        .order_by(DraftSource.rank)
        .all()
    )
    return DraftOut(
        id=draft.id,
        body=draft.body,
        confidence=draft.confidence,
        status=draft.status,
        provider=draft.provider,
        edited_by_id=draft.edited_by_id,
        approved_by_id=draft.approved_by_id,
        approved_at=draft.approved_at,
        sent_at=draft.sent_at,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        sources=[
            DraftSourceOut(
                id=item.id,
                source_id=item.source_id,
                chunk_id=item.chunk_id,
                title=item.source.title,
                source_url=item.source.source_url,
                rank=item.rank,
                score=item.score,
                quote=item.quote,
            )
            for item in sources
        ],
    )


def present_conversation(db: Session, conversation: Conversation) -> ConversationDetailOut:
    latest = max(conversation.drafts, key=lambda item: item.created_at) if conversation.drafts else None
    return ConversationDetailOut(
        id=conversation.id,
        public_reference=conversation.public_reference,
        customer_name=conversation.customer_name,
        customer_email=conversation.customer_email,
        customer_company=conversation.customer_company,
        subject=conversation.subject,
        status=conversation.status,
        category=conversation.category,
        intent=conversation.intent,
        urgency=conversation.urgency,
        assigned_to_id=conversation.assigned_to_id,
        is_demo=conversation.is_demo,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageOut.model_validate(message) for message in conversation.messages],
        draft=present_draft(db, latest),
    )

