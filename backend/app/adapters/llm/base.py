from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Classification:
    category: str
    intent: str
    urgency: str


@dataclass
class RetrievedContext:
    rank: int
    title: str
    content: str
    score: float


@dataclass
class GeneratedDraft:
    body: str
    confidence: float


class LLMAdapter(Protocol):
    name: str

    def classify(self, subject: str, message: str) -> Classification: ...

    def draft(self, subject: str, message: str, context: list[RetrievedContext]) -> GeneratedDraft: ...

