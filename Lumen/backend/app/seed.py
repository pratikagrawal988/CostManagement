from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from .connectors import load_provider_manifests, sync_provider_connections
from .models import Customer, ProductRate, SignalSample, Tenant, utcnow
from .recommendations import import_catalog
from .settings import Settings
from .seed_cost_mappings import seed_all_mappings
from .seed_ai_demo import seed_ai_demo_data
from .seed_focus_csp import seed_csp_focus_data
from .focus_aggregator import build_aggregations_from_focus

DEMO_EMAIL    = "admin@demo.local"
DEMO_PASSWORD = "finops2024"


async def seed_everything(db: Session, settings: Settings) -> dict:
    ensure_tenants(db)
    seed_demo_user(db)
    seed_product_catalog(db, settings.resolve_config_path(settings.product_catalog_seed_path))
    catalog_result = import_catalog(db, settings.resolve_config_path(settings.catalog_path))
    manifests = load_provider_manifests(settings.resolve_config_path(settings.provider_registry_path))
    await sync_provider_connections(db, "tenant-demo", manifests)
    seed_signal_history(db)
    cost_mappings = seed_all_mappings("tenant-demo")
    ai_demo = seed_ai_demo_data(db, "tenant-demo")
    csp_demo = seed_csp_focus_data(db, "tenant-demo")
    agg_result = build_aggregations_from_focus(db, "tenant-demo")
    return {
        "catalog": catalog_result,
        "providers": len(manifests),
        "cost_mappings": cost_mappings,
        "ai_demo": ai_demo,
        "csp_demo": csp_demo,
        "aggregations": agg_result,
    }


def ensure_tenants(db: Session) -> None:
    tenant = db.get(Tenant, "tenant-demo")
    if not tenant:
        db.add(Tenant(id="tenant-demo", name="FinOps Demo Tenant"))
    customers = [
        Customer(
            id="cust-acme",
            tenant_id="tenant-demo",
            name="Acme Retail",
            business_unit="Retail",
            cost_center="CC-1001",
            owner_group="finops-retail-owners",
            tags={"env": "prod", "app": "commerce"},
        ),
        Customer(
            id="cust-globex",
            tenant_id="tenant-demo",
            name="Globex Manufacturing",
            business_unit="Manufacturing",
            cost_center="CC-2030",
            owner_group="finops-manufacturing-owners",
            tags={"env": "non-prod", "app": "analytics"},
        ),
        Customer(
            id="cust-umbrella",
            tenant_id="tenant-demo",
            name="Umbrella Research",
            business_unit="AI Research",
            cost_center="CC-9001",
            owner_group="finops-ai-owners",
            tags={"env": "prod", "app": "genai"},
        ),
    ]
    for customer in customers:
        existing = db.get(Customer, customer.id)
        if not existing:
            db.add(customer)
    db.commit()


def seed_product_catalog(db: Session, path: Path) -> None:
    if db.query(ProductRate).count() > 0 or not path.exists():
        return
    snapshot = f"seed-{utcnow().strftime('%Y%m%d')}"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            attrs = {}
            for item in (row.get("attributes") or "").split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    attrs[key.strip()] = value.strip()
            db.add(
                ProductRate(
                    provider=row["provider"],
                    resource_type=row["resource_type"],
                    sku=row["sku"],
                    region=row["region"],
                    pricing_model=row["pricing_model"],
                    unit=row["unit"],
                    rate=float(row["rate"]),
                    compatibility_group=row["compatibility_group"],
                    attributes=attrs,
                    snapshot_id=snapshot,
                    stale_after=utcnow() + timedelta(days=7),
                )
            )
    db.commit()


def seed_signal_history(db: Session) -> None:
    if db.query(SignalSample).count() > 0:
        return
    now = utcnow()
    rows = [
        ("cust-acme", "AWS", "aws-prod", "i-acme-idle-001", "vm", "us-east-1", "m6i.large", "compute.vm.cpu_utilisation_pct", 2.1, "%"),
        ("cust-acme", "AWS", "aws-prod", "i-acme-idle-001", "vm", "us-east-1", "m6i.large", "compute.vm.network_egress_mbps", 0.02, "Mbps"),
        ("cust-acme", "AWS", "aws-prod", "i-acme-idle-001", "vm", "us-east-1", "m6i.large", "storage.volume.iops", 2, "count"),
        ("cust-acme", "AWS", "aws-prod", "i-acme-rightsize-002", "vm", "us-east-1", "m6i.large", "compute.vm.cpu_utilisation_pct", 28, "%"),
        ("cust-acme", "AWS", "aws-prod", "i-acme-rightsize-002", "vm", "us-east-1", "m6i.large", "compute.vm.memory_utilisation_pct", 45, "%"),
        ("cust-globex", "Azure", "az-sub-001", "vm-globex-idle-001", "vm", "eastus", "Standard_D2s_v5", "compute.vm.cpu_utilisation_pct", 3.6, "%"),
        ("cust-globex", "Azure", "az-sub-001", "vm-globex-idle-001", "vm", "eastus", "Standard_D2s_v5", "compute.vm.network_egress_mbps", 0.04, "Mbps"),
        ("cust-globex", "Azure", "az-sub-001", "vm-globex-idle-001", "vm", "eastus", "Standard_D2s_v5", "storage.volume.iops", 3, "count"),
        ("cust-umbrella", "GCP", "gcp-proj-ai", "gcp-ai-vm-001", "vm", "us-central1", "n2-standard-2", "compute.vm.cpu_utilisation_pct", 33, "%"),
        ("cust-umbrella", "FinOps", "ai-gateway", "litellm-prod", "ai_gateway", "global", "gpt-4o", "ai.llm.cache_hit_pct", 12, "%"),
        ("cust-umbrella", "FinOps", "ai-gateway", "litellm-prod", "ai_gateway", "global", "gpt-4o", "ai.llm.prompt_tokens", 420000, "tokens"),
        ("cust-umbrella", "FinOps", "ai-gateway", "litellm-prod", "ai_gateway", "global", "gpt-4o", "billing.resource.cost", 980, "USD"),
    ]
    for day in range(0, 35, 5):
        for row in rows:
            db.add(
                SignalSample(
                    tenant_id="tenant-demo",
                    customer_id=row[0],
                    provider=row[1],
                    account_id=row[2],
                    resource_id=row[3],
                    resource_type=row[4],
                    region=row[5],
                    sku=row[6],
                    signal_name=row[7],
                    value=row[8],
                    unit=row[9],
                    sampled_at=now - timedelta(days=day),
                    dimensions={"seeded": True},
                )
            )
    db.commit()


def seed_demo_user(db: Session) -> None:
    """
    Ensure the demo admin user exists so the login page works out of the box.
    Credentials: admin@demo.local / finops2024
    Idempotent — skips if user already exists.
    """
    from .models import User, new_id
    from .auth import hash_password

    existing = db.query(User).filter_by(email=DEMO_EMAIL).first()
    if existing:
        return

    # Ensure the demo tenant exists first
    tenant = db.get(Tenant, "tenant-demo")
    if not tenant:
        tenant = Tenant(id="tenant-demo", name="FinOps Demo Tenant", status="active")
        db.add(tenant)
        db.flush()

    user = User(
        id              = new_id(),
        tenant_id       = "tenant-demo",
        email           = DEMO_EMAIL,
        hashed_password = hash_password(DEMO_PASSWORD),
        full_name       = "Demo Admin",
        role            = "admin",
        is_active       = True,
    )
    db.add(user)
    db.commit()
