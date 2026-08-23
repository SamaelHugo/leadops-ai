from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Conversation, Message, ResponseDraft, User
from ..presenters import present_conversation, present_draft
from ..schemas import (
    AssignmentUpdate,
    ConversationDetailOut,
    ConversationListOut,
    DraftOut,
    DraftUpdate,
    EscalationRequest,
    SendResult,
)
from ..services.audit import log_activity
from ..services.conversations import (
    approve_draft,
    edit_draft,
    generate_draft,
    latest_draft,
    send_approved_draft,
)


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conversation_or_404(db: Session, organization_id: str, conversation_id: str) -> Conversation:
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.get("", response_model=list[ConversationListOut])
def list_conversations(
    status: str | None = None,
    search: str | None = Query(default=None, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    query = db.query(Conversation).filter(Conversation.organization_id == user.organization_id)
    if status and status != "all":
        query = query.filter(Conversation.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Conversation.customer_name.ilike(term),
                Conversation.customer_email.ilike(term),
                Conversation.subject.ilike(term),
                Conversation.public_reference.ilike(term),
            )
        )
    return query.order_by(desc(Conversation.updated_at)).all()


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailOut:
    return present_conversation(
        db, _conversation_or_404(db, user.organization_id, conversation_id)
    )


@router.post("/{conversation_id}/draft", response_model=DraftOut)
def regenerate_draft(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DraftOut:
    conversation = _conversation_or_404(db, user.organization_id, conversation_id)
    if conversation.status == "sent":
        raise HTTPException(status_code=409, detail="A sent response cannot be regenerated.")
    customer_message = (
        db.query(Message)
        .filter(
            Message.organization_id == user.organization_id,
            Message.conversation_id == conversation.id,
            Message.role == "customer",
        )
        .order_by(desc(Message.created_at))
        .first()
    )
    if customer_message is None:
        raise HTTPException(status_code=409, detail="This conversation has no customer message.")
    draft = generate_draft(
        db,
        conversation=conversation,
        user_message=customer_message.body,
        user_id=user.id,
    )
    conversation.status = "needs_review"
    db.commit()
    db.refresh(draft)
    return present_draft(db, draft)


@router.patch("/{conversation_id}/draft", response_model=DraftOut)
def update_draft(
    conversation_id: str,
    payload: DraftUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DraftOut:
    conversation = _conversation_or_404(db, user.organization_id, conversation_id)
    try:
        draft = edit_draft(db, conversation=conversation, body=payload.body, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return present_draft(db, draft)


@router.post("/{conversation_id}/approve", response_model=DraftOut)
def approve(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DraftOut:
    conversation = _conversation_or_404(db, user.organization_id, conversation_id)
    try:
        draft = approve_draft(db, conversation=conversation, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return present_draft(db, draft)


@router.post("/{conversation_id}/send", response_model=SendResult)
def send(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendResult:
    conversation = _conversation_or_404(db, user.organization_id, conversation_id)
    try:
        outcome = send_approved_draft(db, conversation=conversation, user_id=user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SendResult(
        conversation=ConversationListOut.model_validate(outcome.conversation),
        crm_record=outcome.crm_record,
        webhook_delivery=outcome.webhook_delivery,
    )


@router.patch("/{conversation_id}/assignment", response_model=ConversationListOut)
def assign(
    conversation_id: str,
    payload: AssignmentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = _conversation_or_404(db, user.organization_id, conversation_id)
    if payload.user_id:
        assignee = (
            db.query(User)
            .filter(
                User.id == payload.user_id,
                User.organization_id == user.organization_id,
                User.is_active.is_(True),
            )
            .one_or_none()
        )
        if assignee is None:
            raise HTTPException(status_code=404, detail="Team member not found.")
    conversation.assigned_to_id = payload.user_id
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        conversation_id=conversation.id,
        action="conversation.assigned",
        entity_type="conversation",
        entity_id=conversation.id,
        details={"assigned_to_id": payload.user_id},
        is_demo=conversation.is_demo,
    )
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/{conversation_id}/escalate", response_model=ConversationListOut)
def escalate(
    conversation_id: str,
    payload: EscalationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = _conversation_or_404(db, user.organization_id, conversation_id)
    if payload.user_id:
        assignee = (
            db.query(User)
            .filter(
                User.id == payload.user_id,
                User.organization_id == user.organization_id,
                User.is_active.is_(True),
            )
            .one_or_none()
        )
        if assignee is None:
            raise HTTPException(status_code=404, detail="Team member not found.")
        conversation.assigned_to_id = assignee.id
    conversation.status = "escalated"
    if payload.note:
        db.add(
            Message(
                organization_id=user.organization_id,
                conversation_id=conversation.id,
                role="internal",
                body=payload.note,
                status="note",
                created_by_id=user.id,
                is_demo=conversation.is_demo,
            )
        )
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        conversation_id=conversation.id,
        action="conversation.escalated",
        entity_type="conversation",
        entity_id=conversation.id,
        details={"assigned_to_id": payload.user_id, "has_note": bool(payload.note)},
        is_demo=conversation.is_demo,
    )
    db.commit()
    db.refresh(conversation)
    return conversation

