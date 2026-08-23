from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=160)
    organization_slug: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_name: str = Field(min_length=2, max_length=160)
    admin_email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    organization_slug: str
    email: EmailStr
    password: str


class OrganizationOut(ORMModel):
    id: str
    name: str
    slug: str
    is_demo: bool


class UserOut(ORMModel):
    id: str
    organization_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_demo: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    organization: OrganizationOut


class TeamMemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    role: Literal["admin", "employee"] = "employee"


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class KnowledgeSourceOut(ORMModel):
    id: str
    organization_id: str
    kind: str
    title: str
    source_url: str | None
    mime_type: str | None
    byte_size: int
    status: str
    error: str | None
    chunk_count: int
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class URLSourceCreate(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=255)


class TextSourceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=20, max_length=500_000)


class PublicInquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    company: str | None = Field(default=None, max_length=180)
    subject: str = Field(min_length=3, max_length=255)
    message: str = Field(min_length=10, max_length=20_000)


class PublicInquiryOut(BaseModel):
    reference: str
    status: str
    message: str


class PublicReplyOut(BaseModel):
    body: str
    sent_at: datetime


class PublicInquiryStatusOut(BaseModel):
    reference: str
    subject: str
    status: str
    replies: list[PublicReplyOut]


class MessageOut(ORMModel):
    id: str
    role: str
    body: str
    status: str
    created_by_id: str | None
    created_at: datetime


class DraftSourceOut(BaseModel):
    id: str
    source_id: str
    chunk_id: str
    title: str
    source_url: str | None
    rank: int
    score: float
    quote: str


class DraftOut(ORMModel):
    id: str
    body: str
    confidence: float
    status: str
    provider: str
    edited_by_id: str | None
    approved_by_id: str | None
    approved_at: datetime | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
    sources: list[DraftSourceOut] = []


class ConversationListOut(ORMModel):
    id: str
    public_reference: str
    customer_name: str
    customer_email: str
    customer_company: str | None
    subject: str
    status: str
    category: str
    intent: str
    urgency: str
    assigned_to_id: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationListOut):
    messages: list[MessageOut]
    draft: DraftOut | None


class DraftUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=50_000)


class AssignmentUpdate(BaseModel):
    user_id: str | None = None


class EscalationRequest(BaseModel):
    user_id: str | None = None
    note: str | None = Field(default=None, max_length=2_000)


class IntegrationOut(ORMModel):
    id: str
    kind: str
    provider: str
    enabled: bool
    config: dict[str, Any]
    has_secret: bool = False
    last_test_status: str | None
    last_test_error: str | None
    is_demo: bool
    updated_at: datetime


class CRMIntegrationUpdate(BaseModel):
    provider: Literal["test", "hubspot"]
    access_token: str | None = Field(default=None, max_length=4_000)
    enabled: bool = True
    create_object: Literal["ticket", "deal"] = "ticket"
    pipeline: str | None = Field(default=None, max_length=100)
    stage: str | None = Field(default=None, max_length=100)

    @field_validator("access_token")
    @classmethod
    def token_required_for_hubspot(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class N8NIntegrationUpdate(BaseModel):
    webhook_url: HttpUrl
    signing_secret: str | None = Field(default=None, max_length=1_000)
    enabled: bool = True


class CRMRecordOut(ORMModel):
    id: str
    conversation_id: str
    provider: str
    object_type: str
    external_id: str
    payload: dict[str, Any]
    is_demo: bool
    created_at: datetime


class WebhookDeliveryOut(ORMModel):
    id: str
    conversation_id: str | None
    event: str
    target_url: str
    status: str
    attempt_count: int
    response_status: int | None
    response_body: str | None
    last_error: str | None
    is_demo: bool
    created_at: datetime
    last_attempt_at: datetime | None
    delivered_at: datetime | None


class ActivityLogOut(ORMModel):
    id: str
    user_id: str | None
    conversation_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    level: str
    details: dict[str, Any]
    is_demo: bool
    created_at: datetime


class AnalyticsOut(BaseModel):
    total_conversations: int
    needs_review: int
    sent: int
    escalated: int
    average_confidence: float
    webhook_failures: int
    by_category: dict[str, int]
    last_seven_days: list[dict[str, int | str]]


class SendResult(BaseModel):
    conversation: ConversationListOut
    crm_record: CRMRecordOut | None
    webhook_delivery: WebhookDeliveryOut | None
