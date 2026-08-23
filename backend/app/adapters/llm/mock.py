from __future__ import annotations

from .base import Classification, GeneratedDraft, RetrievedContext


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
                    "Спасибо за обращение. В базе знаний не нашлось достаточно данных для "
                    "точного ответа. Перед отправкой сотрудник уточнит детали и ответит вручную."
                ),
                confidence=0.18,
            )
        best = context[0]
        excerpts = []
        for item in context[:3]:
            excerpt = item.content.strip()
            if len(excerpt) > 320:
                excerpt = excerpt[:317].rstrip() + "..."
            excerpts.append(f"[{item.rank}] {excerpt}")
        body = (
            "Спасибо за обращение. По информации из нашей базы знаний:\n\n"
            + "\n\n".join(excerpts)
            + "\n\nЕсли этот ответ не закрывает вопрос, сотрудник уточнит детали перед отправкой."
        )
        confidence = min(0.94, max(0.25, 0.45 + best.score * 0.5))
        return GeneratedDraft(body=body, confidence=round(confidence, 3))

