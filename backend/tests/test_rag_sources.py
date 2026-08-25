from __future__ import annotations

from app.schemas import PublicInquiryCreate
from app.services.conversations import create_public_inquiry, latest_draft
from app.services.knowledge import create_and_index_source
from conftest import create_tenant


def test_rag_draft_keeps_traceable_sources(db):
    organization, user = create_tenant(db, slug="rag")
    source = create_and_index_source(
        db,
        organization_id=organization.id,
        created_by_id=user.id,
        kind="text",
        title="Warranty policy",
        text="The NX-24 controller has a two-year warranty. Damaged deliveries need a photo.",
    )
    conversation = create_public_inquiry(
        db,
        organization_id=organization.id,
        payload=PublicInquiryCreate(
            name="Customer",
            email="customer@example.com",
            subject="NX-24 warranty",
            message="How long is the warranty for the NX-24 controller?",
        ),
    )
    draft = latest_draft(db, conversation)

    assert draft is not None
    assert draft.sources
    assert draft.sources[0].source_id == source.id
    assert "warranty" in draft.sources[0].quote.lower()
    assert "[1]" in draft.body
    assert 0 < draft.confidence <= 1


def test_mock_draft_prefers_sentences_that_match_the_inquiry(db):
    organization, user = create_tenant(db, slug="relevant-draft")
    create_and_index_source(
        db,
        organization_id=organization.id,
        created_by_id=user.id,
        kind="text",
        title="Sales and support guide",
        text=(
            "Priority support replies within two business hours. "
            "Damaged deliveries need an order number and a photo. "
            "Orders above 50 units qualify for volume pricing. "
            "A sales specialist prepares the quote after receiving the required quantity."
        ),
    )
    conversation = create_public_inquiry(
        db,
        organization_id=organization.id,
        payload=PublicInquiryCreate(
            name="Customer",
            email="pricing@example.com",
            subject="Volume price for 80 units",
            message="How does volume pricing work for an order of 80 units?",
        ),
    )
    draft = latest_draft(db, conversation)

    assert draft is not None
    assert "Orders above 50 units qualify for volume pricing." in draft.body
    assert "Priority support" not in draft.body
