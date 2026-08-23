from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...models import Conversation


@dataclass
class CRMResult:
    provider: str
    object_type: str
    external_id: str
    payload: dict


class CRMAdapter(Protocol):
    name: str

    def test_connection(self) -> None: ...

    def upsert(self, conversation: Conversation, response_body: str) -> CRMResult: ...

