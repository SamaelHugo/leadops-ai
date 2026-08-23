from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Message, Organization
from ..schemas import (
    PublicInquiryCreate,
    PublicInquiryOut,
    PublicInquiryStatusOut,
    PublicReplyOut,
)
from ..services.conversations import create_public_inquiry


router = APIRouter(prefix="/api/public", tags=["public"])


class PublicFormConfig(BaseModel):
    organization_name: str
    organization_slug: str
    is_demo: bool


@router.get("/{organization_slug}", response_model=PublicFormConfig)
def public_form_config(
    organization_slug: str, db: Session = Depends(get_db)
) -> PublicFormConfig:
    organization = (
        db.query(Organization).filter(Organization.slug == organization_slug).one_or_none()
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="This contact form is not available.")
    return PublicFormConfig(
        organization_name=organization.name,
        organization_slug=organization.slug,
        is_demo=organization.is_demo,
    )


@router.post("/{organization_slug}/inquiries", response_model=PublicInquiryOut, status_code=201)
def submit_inquiry(
    organization_slug: str,
    payload: PublicInquiryCreate,
    db: Session = Depends(get_db),
) -> PublicInquiryOut:
    organization = (
        db.query(Organization).filter(Organization.slug == organization_slug).one_or_none()
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="This contact form is not available.")
    try:
        conversation = create_public_inquiry(
            db, organization_id=organization.id, payload=payload
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="We could not process the inquiry. Please try again in a moment.",
        ) from exc
    return PublicInquiryOut(
        reference=conversation.public_reference,
        status=conversation.status,
        message="Your message is in the inbox. A team member will review the reply before it is sent.",
    )


@router.get(
    "/{organization_slug}/inquiries/{reference}",
    response_model=PublicInquiryStatusOut,
)
def inquiry_status(
    organization_slug: str,
    reference: str,
    email: EmailStr = Query(...),
    db: Session = Depends(get_db),
) -> PublicInquiryStatusOut:
    conversation = (
        db.query(Conversation)
        .join(Organization, Organization.id == Conversation.organization_id)
        .filter(
            Organization.slug == organization_slug,
            Conversation.public_reference == reference.upper(),
            Conversation.customer_email == str(email).lower(),
        )
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Reference and email did not match an inquiry.")
    replies = (
        db.query(Message)
        .filter(
            Message.organization_id == conversation.organization_id,
            Message.conversation_id == conversation.id,
            Message.role == "employee",
            Message.status == "sent",
        )
        .order_by(Message.created_at)
        .all()
    )
    return PublicInquiryStatusOut(
        reference=conversation.public_reference,
        subject=conversation.subject,
        status=conversation.status,
        replies=[PublicReplyOut(body=message.body, sent_at=message.created_at) for message in replies],
    )
