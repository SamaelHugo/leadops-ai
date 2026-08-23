from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

import httpx
import numpy as np
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import engine
from ..models import KnowledgeChunk, KnowledgeSource
from .text import split_text


TOKEN_PATTERN = re.compile(r"[\wа-яёА-ЯЁ]+", re.UNICODE)


@dataclass
class SearchHit:
    chunk_id: str
    source_id: str
    title: str
    source_url: str | None
    content: str
    score: float
    rank: int


def _local_embedding(text: str, dim: int) -> list[float]:
    vector = np.zeros(dim, dtype=np.float32)
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    grams = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]
    for gram in grams:
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=16).digest()
        bucket = int.from_bytes(digest[:8], "big") % dim
        sign = 1.0 if digest[8] & 1 == 0 else -1.0
        vector[bucket] += sign
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    if settings.embeddings_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("EMBEDDINGS_PROVIDER=openai requires OPENAI_API_KEY")
        output: list[list[float]] = []
        for start in range(0, len(texts), 128):
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "text-embedding-3-small",
                    "input": texts[start : start + 128],
                    "dimensions": settings.embedding_dim,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            rows = sorted(response.json()["data"], key=lambda row: row["index"])
            output.extend(row["embedding"] for row in rows)
        return output
    return [_local_embedding(text, settings.embedding_dim) for text in texts]


def index_source(db: Session, source: KnowledgeSource, text: str) -> KnowledgeSource:
    settings = get_settings()
    pieces = split_text(text, settings.chunk_size, settings.chunk_overlap)
    if not pieces:
        raise ValueError("No readable text was found in this source.")
    vectors = embed_texts(pieces)
    db.query(KnowledgeChunk).filter(
        KnowledgeChunk.organization_id == source.organization_id,
        KnowledgeChunk.source_id == source.id,
    ).delete(synchronize_session=False)
    for index, (piece, vector) in enumerate(zip(pieces, vectors)):
        db.add(
            KnowledgeChunk(
                organization_id=source.organization_id,
                source_id=source.id,
                chunk_index=index,
                content=piece,
                embedding=vector,
                chunk_meta={"title": source.title, "url": source.source_url},
                is_demo=source.is_demo,
            )
        )
    source.chunk_count = len(pieces)
    source.status = "ready"
    source.error = None
    db.flush()
    return source


def search_knowledge(
    db: Session, *, organization_id: str, query: str, top_k: int | None = None
) -> list[SearchHit]:
    settings = get_settings()
    limit = top_k or settings.rag_top_k
    query_vector = np.array(embed_texts([query])[0], dtype=np.float32)
    if engine.dialect.name == "postgresql":
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector.tolist()).label(
            "distance"
        )
        rows = (
            db.query(KnowledgeChunk, KnowledgeSource, distance)
            .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
            .filter(
                KnowledgeChunk.organization_id == organization_id,
                KnowledgeSource.organization_id == organization_id,
                KnowledgeSource.status == "ready",
            )
            .order_by(distance)
            .limit(limit)
            .all()
        )
        return [
            SearchHit(
                chunk_id=chunk.id,
                source_id=source.id,
                title=source.title,
                source_url=source.source_url,
                content=chunk.content,
                score=max(-1.0, min(1.0, 1.0 - float(distance_value))),
                rank=index,
            )
            for index, (chunk, source, distance_value) in enumerate(rows, start=1)
        ]

    rows = (
        db.query(KnowledgeChunk, KnowledgeSource)
        .join(KnowledgeSource, KnowledgeSource.id == KnowledgeChunk.source_id)
        .filter(
            KnowledgeChunk.organization_id == organization_id,
            KnowledgeSource.organization_id == organization_id,
            KnowledgeSource.status == "ready",
        )
        .all()
    )
    usable = [row for row in rows if len(row[0].embedding or []) == len(query_vector)]
    if not usable:
        return []
    matrix = np.array([chunk.embedding for chunk, _ in usable], dtype=np.float32)
    scores = matrix @ query_vector
    ordering = np.argsort(-scores)[:limit]
    hits: list[SearchHit] = []
    for rank, row_index in enumerate(ordering, start=1):
        chunk, source = usable[int(row_index)]
        hits.append(
            SearchHit(
                chunk_id=chunk.id,
                source_id=source.id,
                title=source.title,
                source_url=source.source_url,
                content=chunk.content,
                score=float(scores[int(row_index)]),
                rank=rank,
            )
        )
    return hits

