from __future__ import annotations

from app.models import Conversation
from conftest import auth_headers, create_tenant


def test_user_cannot_read_another_organizations_conversation(client, db):
    organization_a, user_a = create_tenant(db, slug="tenant-a", email="a@example.com")
    organization_b, _user_b = create_tenant(db, slug="tenant-b", email="b@example.com")
    foreign = Conversation(
        organization_id=organization_b.id,
        customer_name="Other tenant customer",
        customer_email="customer@example.com",
        subject="Private conversation",
    )
    own = Conversation(
        organization_id=organization_a.id,
        customer_name="Own customer",
        customer_email="own@example.com",
        subject="Visible conversation",
    )
    db.add_all([foreign, own])
    db.commit()

    headers = auth_headers(user_a)
    detail = client.get(f"/api/conversations/{foreign.id}", headers=headers)
    inbox = client.get("/api/conversations", headers=headers)

    assert detail.status_code == 404
    assert [item["id"] for item in inbox.json()] == [own.id]

