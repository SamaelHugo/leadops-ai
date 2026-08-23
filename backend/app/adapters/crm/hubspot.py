from __future__ import annotations

from urllib.parse import quote

import httpx

from ...config import get_settings
from ...models import Conversation
from .base import CRMResult


class HubSpotAdapter:
    name = "hubspot"

    def __init__(self, access_token: str, config: dict) -> None:
        self.base_url = get_settings().hubspot_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self.config = config

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = httpx.request(
            method,
            f"{self.base_url}{path}",
            headers=self.headers,
            timeout=30.0,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def test_connection(self) -> None:
        self._request("GET", "/crm/objects/2026-03/contacts", params={"limit": 1})

    def _upsert_contact(self, conversation: Conversation) -> str:
        name_parts = conversation.customer_name.strip().split(maxsplit=1)
        properties = {
            "email": conversation.customer_email,
            "firstname": name_parts[0] if name_parts else conversation.customer_name,
            "lastname": name_parts[1] if len(name_parts) > 1 else "",
            "company": conversation.customer_company or "",
        }
        encoded_email = quote(conversation.customer_email, safe="")
        lookup = httpx.get(
            f"{self.base_url}/crm/objects/2026-03/contacts/{encoded_email}",
            headers=self.headers,
            params={"idProperty": "email"},
            timeout=30.0,
        )
        if lookup.status_code == 404:
            response = self._request(
                "POST", "/crm/objects/2026-03/contacts", json={"properties": properties}
            )
            return str(response.json()["id"])
        lookup.raise_for_status()
        contact_id = str(lookup.json()["id"])
        self._request(
            "PATCH",
            f"/crm/objects/2026-03/contacts/{contact_id}",
            json={"properties": properties},
        )
        return contact_id

    def upsert(self, conversation: Conversation, response_body: str) -> CRMResult:
        contact_id = self._upsert_contact(conversation)
        object_type = str(self.config.get("create_object") or "ticket")
        pipeline = str(self.config.get("pipeline") or ("0" if object_type == "ticket" else "default"))
        stage = str(self.config.get("stage") or ("1" if object_type == "ticket" else "appointmentscheduled"))
        if object_type == "deal":
            properties = {
                "dealname": f"{conversation.customer_company or conversation.customer_name}: {conversation.subject}",
                "pipeline": pipeline,
                "dealstage": stage,
                "description": response_body,
            }
            path_object = "deals"
        else:
            object_type = "ticket"
            properties = {
                "subject": conversation.subject,
                "content": response_body,
                "hs_pipeline": pipeline,
                "hs_pipeline_stage": stage,
            }
            path_object = "tickets"
        created = self._request(
            "POST",
            f"/crm/objects/2026-03/{path_object}",
            json={"properties": properties},
        ).json()
        external_id = str(created["id"])
        self._request(
            "PUT",
            f"/crm/objects/2026-03/{path_object}/{external_id}/associations/default/contacts/{contact_id}",
        )
        return CRMResult(
            provider=self.name,
            object_type=object_type,
            external_id=external_id,
            payload={"contact_id": contact_id, "record": created},
        )
