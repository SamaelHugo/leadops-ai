from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..dependencies import get_current_user
from ..models import Integration, Organization, User
from ..schemas import AuthResponse, LoginRequest, OrganizationCreate, OrganizationOut, UserOut
from ..services.audit import log_activity


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
        ),
        user=UserOut.model_validate(user),
        organization=OrganizationOut.model_validate(user.organization),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register_organization(payload: OrganizationCreate, db: Session = Depends(get_db)) -> AuthResponse:
    if db.query(Organization).filter(Organization.slug == payload.organization_slug).first():
        raise HTTPException(status_code=409, detail="This organization URL is already in use.")
    organization = Organization(name=payload.organization_name, slug=payload.organization_slug)
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        email=str(payload.admin_email).lower(),
        full_name=payload.admin_name,
        password_hash=hash_password(payload.password),
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
    log_activity(
        db,
        organization_id=organization.id,
        user_id=user.id,
        action="organization.created",
        entity_type="organization",
        entity_id=organization.id,
        details={"name": organization.name},
    )
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = (
        db.query(User)
        .join(Organization, Organization.id == User.organization_id)
        .filter(
            Organization.slug == payload.organization_slug,
            User.email == str(payload.email).lower(),
            User.is_active.is_(True),
        )
        .one_or_none()
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Organization, email, or password is incorrect.")
    return _auth_response(user)


@router.get("/me", response_model=AuthResponse)
def me(user: User = Depends(get_current_user)) -> AuthResponse:
    return _auth_response(user)

