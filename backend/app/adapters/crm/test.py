from __future__ import annotations

import hashlib

from ...models import Conversation
from .base import CRMResult


class TestCRMAdapter:
    name = "test"

    def test_connection(self) -> None:
        return None

    def upsert(self, conversation: Conversation, response_body: str) -> CRMResult:
        record_id = "demo_" + hashlib.sha256(conversation.id.encode()).hexdigest()[:12]
        return CRMResult(
            provider=self.name,
            object_type="ticket",
            external_id=record_id,
            payload={
                "demo": True,
                "contact": {
                    "name": conversation.customer_name,
                    "email": conversation.customer_email,
                    "company": conversation.customer_company,
                },
                "ticket": {
                    "subject": conversation.subject,
                    "status": "new",
                    "category": conversation.category,
                    "urgency": conversation.urgency,
                    "approved_response": response_body,
                },
            },
        )

