from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import KnowledgeSource
from .audit import log_activity
from .rag import index_source


def create_and_index_source(
    db: Session,
    *,
    organization_id: str,
    created_by_id: str | None,
    kind: str,
    title: str,
    text: str,
    source_url: str | None = None,
    mime_type: str | None = None,
    byte_size: int | None = None,
    is_demo: bool = False,
) -> KnowledgeSource:
    source = KnowledgeSource(
        organization_id=organization_id,
        created_by_id=created_by_id,
        kind=kind,
        title=title,
        source_url=source_url,
        mime_type=mime_type,
        byte_size=byte_size if byte_size is not None else len(text.encode("utf-8")),
        status="processing",
        is_demo=is_demo,
    )
    db.add(source)
    db.flush()
    try:
        index_source(db, source, text)
        log_activity(
            db,
            organization_id=organization_id,
            user_id=created_by_id,
            action="knowledge.indexed",
            entity_type="knowledge_source",
            entity_id=source.id,
            details={"title": source.title, "chunks": source.chunk_count, "kind": kind},
            is_demo=is_demo,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        source = KnowledgeSource(
            id=source.id,
            organization_id=organization_id,
            created_by_id=created_by_id,
            kind=kind,
            title=title,
            source_url=source_url,
            mime_type=mime_type,
            byte_size=byte_size if byte_size is not None else len(text.encode("utf-8")),
            status="failed",
            error=str(exc)[:2_000],
            is_demo=is_demo,
        )
        db.merge(source)
        log_activity(
            db,
            organization_id=organization_id,
            user_id=created_by_id,
            action="knowledge.failed",
            entity_type="knowledge_source",
            entity_id=source.id,
            level="error",
            details={"title": title, "error": str(exc)},
            is_demo=is_demo,
        )
        db.commit()
        raise
    db.refresh(source)
    return source

