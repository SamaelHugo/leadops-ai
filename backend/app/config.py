from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_database_url() -> str:
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/leadops.db"
    return "sqlite:///./leadops.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = Field(default_factory=default_database_url)
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "http://localhost:3000"
    jwt_secret: str = ""
    encryption_key: str | None = None
    access_token_minutes: int = 720

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    embeddings_provider: str = "local"
    embedding_dim: int = 384
    chunk_size: int = 900
    chunk_overlap: int = 140
    rag_top_k: int = 4

    max_upload_mb: int = 15
    max_url_bytes: int = 2_000_000
    allow_private_url_sources: bool = False
    hubspot_base_url: str = "https://api.hubapi.com"
    webhook_timeout_seconds: float = 8.0
    seed_demo_data: bool = True

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"mock", "openai"}:
            raise ValueError("LLM_PROVIDER must be mock or openai")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def fernet_key(self) -> bytes:
        if self.encryption_key:
            return self.encryption_key.encode("utf-8")
        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET must be set before storing integration secrets")
        digest = hashlib.sha256(self.jwt_secret.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


@lru_cache
def get_settings() -> Settings:
    return Settings()
