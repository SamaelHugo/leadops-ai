from __future__ import annotations

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp(prefix='leadops-tests-')}/tests.db"
os.environ["JWT_SECRET"] = "leadops-test-secret-not-for-production"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDINGS_PROVIDER"] = "local"

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Integration, Organization, User


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def create_tenant(db, *, slug: str, email: str = "admin@example.com"):
    organization = Organization(name=f"{slug} company", slug=slug)
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        email=email,
        full_name="Test Admin",
        password_hash=hash_password("password-123"),
        role="admin",
    )
    db.add(user)
    db.flush()
    db.add(
        Integration(
            organization_id=organization.id,
            kind="crm",
            provider="test",
            enabled=True,
            config={"create_object": "ticket"},
        )
    )
    db.commit()
    db.refresh(user)
    return organization, user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
    )
    return {"Authorization": f"Bearer {token}"}

