from __future__ import annotations

from app.database import Base


def test_every_tenant_owned_table_has_organization_id():
    tenant_root_tables = {"organizations"}
    system_tables = {"alembic_version"}
    for table in Base.metadata.sorted_tables:
        if table.name in tenant_root_tables | system_tables:
            continue
        assert "organization_id" in table.columns, f"{table.name} is missing organization_id"

