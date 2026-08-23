from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..adapters.crm import test_crm_connection
from ..auth import encrypt_secret
from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Integration, User
from ..schemas import CRMIntegrationUpdate, IntegrationOut, N8NIntegrationUpdate
from ..services.audit import log_activity


router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def _present(integration: Integration) -> IntegrationOut:
    return IntegrationOut(
        id=integration.id,
        kind=integration.kind,
        provider=integration.provider,
        enabled=integration.enabled,
        config=integration.config or {},
        has_secret=bool(integration.encrypted_secret),
        last_test_status=integration.last_test_status,
        last_test_error=integration.last_test_error,
        is_demo=integration.is_demo,
        updated_at=integration.updated_at,
    )


@router.get("", response_model=list[IntegrationOut])
def list_integrations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[IntegrationOut]:
    rows = (
        db.query(Integration)
        .filter(Integration.organization_id == user.organization_id)
        .order_by(Integration.kind)
        .all()
    )
    return [_present(row) for row in rows]


@router.put("/crm", response_model=IntegrationOut)
def configure_crm(
    payload: CRMIntegrationUpdate,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> IntegrationOut:
    integration = (
        db.query(Integration)
        .filter(
            Integration.organization_id == user.organization_id,
            Integration.kind == "crm",
        )
        .one_or_none()
    )
    if integration is None:
        integration = Integration(
            organization_id=user.organization_id,
            kind="crm",
            provider=payload.provider,
            is_demo=payload.provider == "test",
        )
        db.add(integration)
    if payload.provider == "hubspot" and not payload.access_token:
        if integration.provider != "hubspot" or not integration.encrypted_secret:
            raise HTTPException(status_code=422, detail="Enter a HubSpot private app access token.")
    integration.provider = payload.provider
    integration.enabled = payload.enabled
    integration.config = {
        "create_object": payload.create_object,
        "pipeline": payload.pipeline,
        "stage": payload.stage,
    }
    integration.is_demo = payload.provider == "test"
    if payload.access_token:
        integration.encrypted_secret = encrypt_secret(payload.access_token)
    elif payload.provider == "test":
        integration.encrypted_secret = None
    integration.last_test_status = None
    integration.last_test_error = None
    db.flush()
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        action="integration.crm_configured",
        entity_type="integration",
        entity_id=integration.id,
        details={"provider": payload.provider, "enabled": payload.enabled},
        is_demo=integration.is_demo,
    )
    db.commit()
    db.refresh(integration)
    return _present(integration)


@router.post("/crm/test", response_model=IntegrationOut)
def test_crm(
    user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
) -> IntegrationOut:
    integration = (
        db.query(Integration)
        .filter(
            Integration.organization_id == user.organization_id,
            Integration.kind == "crm",
        )
        .one_or_none()
    )
    if integration is None:
        raise HTTPException(status_code=404, detail="CRM is not configured.")
    try:
        test_crm_connection(integration)
        integration.last_test_status = "connected"
        integration.last_test_error = None
    except Exception as exc:
        integration.last_test_status = "failed"
        integration.last_test_error = str(exc)[:2_000]
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        action=(
            "integration.crm_tested"
            if integration.last_test_status == "connected"
            else "integration.crm_test_failed"
        ),
        entity_type="integration",
        entity_id=integration.id,
        level="info" if integration.last_test_status == "connected" else "error",
        details={
            "provider": integration.provider,
            "status": integration.last_test_status,
            "error": integration.last_test_error,
        },
        is_demo=integration.is_demo,
    )
    db.commit()
    db.refresh(integration)
    return _present(integration)


@router.put("/n8n", response_model=IntegrationOut)
def configure_n8n(
    payload: N8NIntegrationUpdate,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> IntegrationOut:
    integration = (
        db.query(Integration)
        .filter(
            Integration.organization_id == user.organization_id,
            Integration.kind == "workflow",
        )
        .one_or_none()
    )
    if integration is None:
        integration = Integration(
            organization_id=user.organization_id,
            kind="workflow",
            provider="n8n",
        )
        db.add(integration)
    integration.provider = "n8n"
    integration.enabled = payload.enabled
    integration.config = {"webhook_url": str(payload.webhook_url)}
    if payload.signing_secret:
        integration.encrypted_secret = encrypt_secret(payload.signing_secret)
    integration.last_test_status = None
    integration.last_test_error = None
    db.flush()
    log_activity(
        db,
        organization_id=user.organization_id,
        user_id=user.id,
        action="integration.n8n_configured",
        entity_type="integration",
        entity_id=integration.id,
        details={"webhook_url": str(payload.webhook_url), "enabled": payload.enabled},
        is_demo=integration.is_demo,
    )
    db.commit()
    db.refresh(integration)
    return _present(integration)

