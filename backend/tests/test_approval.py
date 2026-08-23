from __future__ import annotations

from app.schemas import PublicInquiryCreate
from app.services.conversations import create_public_inquiry
from conftest import auth_headers, create_tenant


def test_response_must_be_approved_before_send(client, db):
    organization, user = create_tenant(db, slug="approval")
    conversation = create_public_inquiry(
        db,
        organization_id=organization.id,
        payload=PublicInquiryCreate(
            name="Customer",
            email="customer@example.com",
            subject="Support question",
            message="Please explain your normal support response time.",
        ),
    )
    headers = auth_headers(user)

    blocked = client.post(f"/api/conversations/{conversation.id}/send", headers=headers)
    approved = client.post(f"/api/conversations/{conversation.id}/approve", headers=headers)
    sent = client.post(f"/api/conversations/{conversation.id}/send", headers=headers)

    assert blocked.status_code == 409
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert sent.status_code == 200
    assert sent.json()["conversation"]["status"] == "sent"
    assert sent.json()["crm_record"]["provider"] == "test"

    portal = client.get(
        f"/api/public/{organization.slug}/inquiries/{conversation.public_reference}",
        params={"email": "customer@example.com"},
    )
    assert portal.status_code == 200
    assert portal.json()["status"] == "sent"
    assert len(portal.json()["replies"]) == 1
