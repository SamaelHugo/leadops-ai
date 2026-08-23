from __future__ import annotations

from app.models import KnowledgeChunk
from app.services.knowledge import create_and_index_source
from conftest import create_tenant


def test_document_is_split_and_embedded_for_its_organization(db):
    organization, user = create_tenant(db, slug="indexing")
    source = create_and_index_source(
        db,
        organization_id=organization.id,
        created_by_id=user.id,
        kind="text",
        title="Support handbook",
        text=("Priority support responds within two hours. " * 120),
    )
    chunks = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.organization_id == organization.id)
        .all()
    )

    assert source.status == "ready"
    assert source.chunk_count == len(chunks)
    assert len(chunks) > 1
    assert all(len(chunk.embedding) == 384 for chunk in chunks)
    assert all(chunk.organization_id == organization.id for chunk in chunks)

