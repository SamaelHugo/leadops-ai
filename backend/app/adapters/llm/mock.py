from __future__ import annotations

import re

from .base import Classification, GeneratedDraft, RetrievedContext


TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "our",
    "the",
    "this",
    "to",
    "us",
    "we",
    "what",
    "when",
    "with",
    "you",
    "your",
}


def _terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if len(token) > 2 and token.lower() not in STOP_WORDS
    }


def _relevant_excerpt(content: str, query: str, limit: int = 360) -> str:
    sentences = [
        item.strip()
        for item in SENTENCE_PATTERN.split(content.strip())
        if item.strip()
    ]
    if not sentences:
        return content.strip()[:limit]
    query_terms = _terms(query)
    scored = []
    for index, sentence in enumerate(sentences):
        overlap = len(query_terms & _terms(sentence))
        scored.append((overlap, index, sentence))
    matching = [item for item in scored if item[0] > 0]
    selected = sorted(matching, key=lambda item: (-item[0], item[1]))[:2]
    if not selected:
        selected = scored[:2]
    excerpt = " ".join(item[2] for item in sorted(selected, key=lambda item: item[1]))
    if len(excerpt) > limit:
        excerpt = excerpt[: limit - 3].rstrip() + "..."
    return excerpt


class MockLLMAdapter:
    name = "mock"

    def classify(self, subject: str, message: str) -> Classification:
        text = f"{subject} {message}".lower()
        if any(word in text for word in ("ошиб", "не работает", "error", "broken", "сбой")):
            category, intent = "support", "incident"
        elif any(word in text for word in ("цена", "стоим", "тариф", "price", "quote", "купить")):
            category, intent = "sales", "pricing"
        elif any(word in text for word in ("возврат", "refund", "отмен")):
            category, intent = "billing", "refund"
        else:
            category, intent = "general", "question"
        urgency = "high" if any(
            word in text for word in ("срочно", "критич", "немедленно", "urgent", "asap", "простой")
        ) else "normal"
        return Classification(category=category, intent=intent, urgency=urgency)

    def draft(
        self, subject: str, message: str, context: list[RetrievedContext]
    ) -> GeneratedDraft:
        if not context:
            return GeneratedDraft(
                body=(
                    "Thanks for your message. The knowledge base does not contain enough "
                    "information for a reliable answer. A team member will check the details "
                    "before replying."
                ),
                confidence=0.18,
            )
        best = context[0]
        query = f"{subject} {message}"
        excerpts = []
        for item in context[:3]:
            excerpt = _relevant_excerpt(item.content, query)
            excerpts.append(f"[{item.rank}] {excerpt}")
        body = (
            "Thanks for your message. Based on the information in our knowledge base:\n\n"
            + "\n\n".join(excerpts)
            + "\n\nA team member will check any missing details before sending this reply."
        )
        confidence = min(0.94, max(0.25, 0.45 + best.score * 0.5))
        return GeneratedDraft(body=body, confidence=round(confidence, 3))
