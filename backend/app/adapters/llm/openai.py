from __future__ import annotations

import json

import httpx

from ...config import get_settings
from .base import Classification, GeneratedDraft, RetrievedContext


class OpenAIAdapter:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.settings = get_settings()

    def _json_completion(self, system: str, user: str) -> dict:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.settings.openai_model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=45.0,
        )
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])

    def classify(self, subject: str, message: str) -> Classification:
        result = self._json_completion(
            "Classify a customer inquiry. Return JSON with category, intent, and urgency. "
            "Urgency must be low, normal, high, or critical.",
            f"Subject: {subject}\nMessage: {message}",
        )
        return Classification(
            category=str(result.get("category") or "general")[:80],
            intent=str(result.get("intent") or "question")[:80],
            urgency=str(result.get("urgency") or "normal")[:20],
        )

    def draft(
        self, subject: str, message: str, context: list[RetrievedContext]
    ) -> GeneratedDraft:
        sources = "\n\n".join(
            f"[{item.rank}] {item.title}\n{item.content}" for item in context
        )
        result = self._json_completion(
            "Write a concise customer support draft using only the supplied sources. "
            "Cite factual claims with [1], [2], and so on. If the sources are insufficient, "
            "say what needs manual clarification. Return JSON with body and confidence from 0 to 1.",
            f"Subject: {subject}\nInquiry: {message}\n\nSources:\n{sources or '(none)'}",
        )
        confidence = min(1.0, max(0.0, float(result.get("confidence") or 0)))
        return GeneratedDraft(body=str(result.get("body") or ""), confidence=confidence)

