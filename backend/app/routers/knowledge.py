from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import KnowledgeSource, User
from ..schemas import KnowledgeSourceOut, TextSourceCreate, URLSourceCreate
from ..services.audit import log_activity
from ..services.knowledge import create_and_index_source
from ..services.text import extract_pdf, fetch_url_text


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeSourceOut])
def list_sources(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[KnowledgeSource]:
    return (
        db.query(KnowledgeSource)
        .filter(KnowledgeSource.organization_id == user.organization_id)
        .order_by(desc(KnowledgeSource.created_at))
        .all()
    )


@router.post("/files", response_model=KnowledgeSourceOut, status_code=201)
async def upload_pdf(
    file: UploadFile = File(...),
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSource:
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Upload a PDF file.")
    raw = await file.read((get_settings().max_upload_mb * 1024 * 1024) + 1)
    if len(raw) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="The PDF is larger than the upload limit.")
    try:
        text, _pages = extract_pdf(raw)
        return create_and_index_source(
            db,
            organization_id=user.organization_id,
            created_by_id=user.id,
            kind="pdf",
            title=filename,
            text=text,
            mime_type="application/pdf",
            byte_size=len(raw),
            is_demo=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"The PDF could not be indexed: {exc}") from exc


@router.post("/urls", response_model=KnowledgeSourceOut, status_code=201)
def add_url(
    payload: URLSourceCreate,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSource:
    try:
        detected_title, text = fetch_url_text(str(payload.url))
        return create_and_index_source(
            db,
            organization_id=user.organization_id,
            created_by_id=user.id,
            kind="url",
            title=payload.title or detected_title,
            text=text,
            source_url=str(payload.url),
            mime_type="text/html",
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"The page could not be indexed: {exc}") from exc


@router.post("/text", response_model=KnowledgeSourceOut, status_code=201)
def add_text(
    payload: TextSourceCreate,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> KnowledgeSource:
    try:
        return create_and_index_source(
            db,
            organization_id=user.organization_id,
            created_by_id=user.id,
            kind="text",
            title=payload.title,
            text=payload.content,
            mime_type="text/plain",
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"The text could not be indexed: {exc}") from exc


@router.delete("/{source_id}", status_code=204)
def delete_source(
    source_id: str,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> None:
    source = (
        db.query(KnowledgeSource)
        .filter(
            KnowledgeSource.id == source_id,
            KnowledgeSource.organization_id == user.organization_id,
        )
        .one_or_none()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        action="knowledge.deleted",
        entity_type="knowledge_source",
        entity_id=source.id,
        details={"title": source.title},
        is_demo=source.is_demo,
    )
    db.delete(source)
    db.commit()

