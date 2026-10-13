"""Замер качества поиска: попадает ли перефразированный вопрос в нужный документ.

Зачем. Обещание «RAG работает» проверяется не ощущением, а числом. Тест задаёт
вопросы, НЕ используя слова из документов, и считает, сколько раз на первом
месте оказался правильный источник. Это и есть retrieval, отдельно от LLM:
если нужный кусок не найден, никакой промпт ответ не спасёт.

Запуск (провайдер берётся из окружения):

    cd backend
    PYTHONPATH=. EMBEDDINGS_PROVIDER=local .venv/bin/python tools/retrieval_eval.py
    PYTHONPATH=. EMBEDDINGS_PROVIDER=openai OPENAI_API_KEY=... .venv/bin/python tools/retrieval_eval.py

Замер 13.10.2026, EMBEDDINGS_PROVIDER=local: Top-1 = 1/5, Top-3 = 4/5. На пяти
документах случайный выбор дал бы Top-1 = 1/5 и Top-3 = 3/5, то есть по первому
месту хеширующий векторизатор не отличим от случайного, а слабый сигнал виден
только в тройке. Причина в том, что он сравнивает совпадение слов, а не смысл:
вопрос про «password» не находит документ, где написано «passphrase».

Практическое следствие. При rag_top_k = 4 нужный кусок часто всё же попадает в
контекст, и на пяти документах демо выглядит рабочим. На реальной базе клиента в
сотни чанков такое ранжирование разваливается, потому что правильный кусок
перестаёт помещаться в top-k. Поэтому публичное демо поднимается на openai,
см. DEPLOY-DEMO.md. Арм с openai здесь не замерен: нужен ключ.
"""

from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp(prefix='leadops-eval-')}/eval.db")
os.environ.setdefault("JWT_SECRET", "retrieval-eval-secret-not-for-production")
os.environ.setdefault("SEED_DEMO_DATA", "false")
os.environ.setdefault("LLM_PROVIDER", "mock")

from app.auth import hash_password
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Organization, User
from app.services.knowledge import create_and_index_source
from app.services.rag import search_knowledge


DOCS = {
    "shipping": (
        "Delivery windows. Orders leave the warehouse the next working day. Ground transport "
        "reaches the destination in three to five days. Express transport arrives the following "
        "morning. Courier handover requires a signature from an adult."
    ),
    "warranty": (
        "Cover for defects. Every controller carries a two year guarantee against manufacturing "
        "faults. A unit that fails is repaired or exchanged at no charge. Damage from water, drops "
        "or incorrect voltage voids the cover."
    ),
    "billing": (
        "Charges and invoices. Accounts are billed monthly in arrears. An invoice is issued on the "
        "first day of each month and payment falls due within fourteen days. Late settlement adds a "
        "two percent monthly surcharge."
    ),
    "accounts": (
        "Signing in. Staff reach the console with an email address and a passphrase. A forgotten "
        "passphrase is reset from the sign in screen using a link sent by mail. Two factor "
        "verification can be switched on per person."
    ),
    "returns": (
        "Sending goods back. An unopened item may be sent back within thirty days for a full refund. "
        "The buyer pays return carriage unless the item was faulty. Refunds reach the original card "
        "within ten working days."
    ),
}

# Вопросы намеренно избегают слов из документов: иначе тест проверяет совпадение
# строк, а не понимание смысла, и любой лексический поиск его пройдёт.
CASES = [
    ("warranty", "My device stopped working by itself. Will you fix it for free?"),
    ("shipping", "How soon can a parcel show up at my door if I pay extra?"),
    ("billing", "What happens if I settle my bill after the deadline?"),
    ("returns", "I changed my mind about an unused purchase. Can I get my money back?"),
    ("accounts", "I cannot remember my password. How do I get back into the system?"),
]


def main() -> int:
    settings = get_settings()
    print(f"провайдер эмбеддингов: {settings.embeddings_provider}, размерность {settings.embedding_dim}\n")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        organization = Organization(name="Retrieval eval", slug="retrieval-eval")
        db.add(organization)
        db.flush()
        admin = User(
            organization_id=organization.id,
            email="eval@example.invalid",
            full_name="Eval",
            password_hash=hash_password("not-a-real-password"),
            role="admin",
        )
        db.add(admin)
        db.commit()

        for title, text in DOCS.items():
            create_and_index_source(
                db,
                organization_id=organization.id,
                created_by_id=admin.id,
                kind="text",
                title=title,
                text=text,
                mime_type="text/plain",
                is_demo=False,
            )
        db.commit()

        hit_at_1 = 0
        hit_at_3 = 0
        for expected, question in CASES:
            hits = search_knowledge(db, organization_id=organization.id, query=question, top_k=3)
            titles = [hit.title for hit in hits]
            top1 = titles[0] if titles else None
            hit_at_1 += top1 == expected
            hit_at_3 += expected in titles
            mark = "ПОПАЛ " if top1 == expected else "ПРОМАХ"
            score = f"{hits[0].score:+.4f}" if hits else "n/a"
            print(f"{mark} ждали={expected:9s} получили={str(top1):9s} score={score}")
            print(f"        {question}")

        total = len(CASES)
        print(f"\nTop-1: {hit_at_1}/{total}   Top-3: {hit_at_3}/{total}")
        print(f"случайный выбор дал бы Top-1 около {total / len(DOCS):.1f}/{total}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
