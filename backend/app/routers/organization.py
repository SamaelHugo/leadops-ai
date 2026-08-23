from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import hash_password
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Organization, User
from ..schemas import (
    OrganizationOut,
    OrganizationUpdate,
    TeamMemberCreate,
    UserOut,
)
from ..services.audit import log_activity


router = APIRouter(prefix="/api/organization", tags=["organization"])


@router.get("", response_model=OrganizationOut)
def get_organization(user: User = Depends(get_current_user)) -> Organization:
    return user.organization


@router.patch("", response_model=OrganizationOut)
def update_organization(
    payload: OrganizationUpdate,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Organization:
    organization = (
        db.query(Organization)
        .filter(Organization.id == user.organization_id)
        .one()
    )
    organization.name = payload.name
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        action="organization.updated",
        entity_type="organization",
        entity_id=organization.id,
        details={"name": payload.name},
        is_demo=organization.is_demo,
    )
    db.commit()
    db.refresh(organization)
    return organization


@router.get("/members", response_model=list[UserOut])
def list_members(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[User]:
    return (
        db.query(User)
        .filter(User.organization_id == user.organization_id)
        .order_by(User.full_name)
        .all()
    )


@router.post("/members", response_model=UserOut, status_code=201)
def create_member(
    payload: TeamMemberCreate,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> User:
    email = str(payload.email).lower()
    if db.query(User).filter(User.organization_id == user.organization_id, User.email == email).first():
        raise HTTPException(status_code=409, detail="A team member with this email already exists.")
    member = User(
        organization_id=user.organization_id,
        full_name=payload.full_name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_demo=user.organization.is_demo,
    )
    db.add(member)
    db.flush()
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        action="team.member_created",
        entity_type="user",
        entity_id=member.id,
        details={"email": email, "role": payload.role},
        is_demo=member.is_demo,
    )
    db.commit()
    db.refresh(member)
    return member

