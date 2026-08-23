from __future__ import annotations

from app.auth import encrypt_secret
from app.models import Conversation, Integration
from app.services.webhooks import dispatch_conversation_webhook
from conftest import auth_headers, create_tenant


class SuccessfulResponse:
    status_code = 200
    text = '{"accepted":true}'

    def raise_for_status(self) -> None:
        return None


def test_failed_n8n_webhook_can_be_retried(client, db, monkeypatch):
    organization, user = create_tenant(db, slug="webhooks")
    workflow = Integration(
        organization_id=organization.id,
        kind="workflow",
        provider="n8n",
        enabled=True,
        config={"webhook_url": "http://127.0.0.1:1/leadops"},
        encrypted_secret=encrypt_secret("test-signing-secret"),
    )
    conversation = Conversation(
        organization_id=organization.id,
        customer_name="Customer",
        customer_email="customer@example.com",
        subject="Retry webhook",
        status="sent",
    )
    db.add_all([workflow, conversation])
    db.commit()
    delivery = dispatch_conversation_webhook(db, conversation=conversation, user_id=user.id)
    db.commit()
    assert delivery is not None
    assert delivery.status == "failed"
    assert delivery.attempt_count == 1

    monkeypatch.setattr("app.services.webhooks.httpx.post", lambda *args, **kwargs: SuccessfulResponse())
    response = client.post(
        f"/api/webhooks/{delivery.id}/retry", headers=auth_headers(user)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "delivered"
    assert response.json()["attempt_count"] == 2

