from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal, init_db
from .routers import (
    activity,
    analytics,
    auth,
    conversations,
    integrations,
    knowledge,
    organization,
    public,
    webhooks,
)
from .seed import seed_demo


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    init_db()
    if settings.seed_demo_data:
        db = SessionLocal()
        try:
            seed_demo(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="LeadOps AI API",
    version="0.1.0",
    description="Multi-tenant inbox, RAG drafts, CRM sync, and n8n workflow delivery.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    organization.router,
    knowledge.router,
    conversations.router,
    integrations.router,
    webhooks.router,
    activity.router,
    analytics.router,
    public.router,
):
    app.include_router(router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "embeddings_provider": settings.embeddings_provider,
        "database": "postgresql" if settings.database_url.startswith("postgres") else "sqlite",
    }


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": "LeadOps AI API", "docs": "/docs", "health": "/api/health"}

