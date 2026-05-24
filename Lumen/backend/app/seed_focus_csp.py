"""
FOCUS v1.0 mock data generator for AWS, Azure, and GCP.

Generates 90 days of realistic cloud cost rows directly into focus_cost.
All rows are fully FOCUS v1.0 compliant — every required and conditional
column is populated.

Cost profile (approximate monthly):
  AWS    ~$13,500  (EC2, S3, RDS, Lambda, CloudFront, EKS, Redshift, SageMaker …)
  Azure  ~$8,200   (VMs, Blob, SQL, AKS, Functions, Cosmos DB, Data Factory …)
  GCP    ~$6,600   (Compute Engine, GCS, Cloud SQL, GKE, BigQuery, Vertex AI …)
  Total  ~$28,300 / month (plus AI layer seeded separately)

Run via seed_everything() on startup — idempotent.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta, timezone
from typing import List

from sqlalchemy.orm import Session

from .models import FocusCost, new_id

SEED_DAYS = 90
TEAMS        = ["platform", "product", "data-science", "growth", "infra"]
TEAM_WEIGHTS = [0.28, 0.26, 0.22, 0.14, 0.10]
ENVS         = ["production", "staging", "development"]
ENV_WEIGHTS  = [0.68, 0.22, 0.10]
COST_CENTERS = ["CC-1010", "CC-2020", "CC-3030", "CC-4040"]


# ─────────────────────────────────────────────────────────────────────────────
# Service catalogue (CSP-specific)
# Each tuple: (service_name, service_category, resource_type, unit, $/unit,
#              avg_daily_qty, regions)
# ─────────────────────────────────────────────────────────────────────────────

AWS_SERVICES = [
    # (name, category, resource_type, unit, price_per_unit, avg_daily_qty, regions)
    ("Amazon EC2",            "Compute",                     "EC2Instance",     "Hrs",      0.096,   1680, ["us-east-1","us-west-2","eu-west-1"]),
    ("Amazon S3",             "Storage",                     "S3Bucket",        "GB-Mo",    0.023,   1100, ["us-east-1","us-west-2","eu-west-1"]),
    ("Amazon RDS",            "Databases",                   "DBInstance",      "Hrs",      0.230,    320, ["us-east-1","us-west-2","eu-west-1"]),
    ("AWS Lambda",            "Compute",                     "LambdaFunction",  "Req",      0.0000002, 8_500_000, ["us-east-1","us-west-2"]),
    ("Amazon CloudFront",     "Networking",                  "Distribution",    "GB",       0.0085,  2200, ["us-east-1","eu-west-1"]),
    ("Amazon EKS",            "Compute",                     "EKSCluster",      "Hrs",      0.100,    720, ["us-east-1","us-west-2","eu-west-1"]),
    ("Amazon CloudWatch",     "Management and Governance",   "LogGroup",        "GB",       0.50,      85, ["us-east-1","us-west-2"]),
    ("Amazon Redshift",       "Analytics",                   "Cluster",         "Hrs",      0.250,    240, ["us-east-1","us-west-2"]),
    ("Amazon SageMaker",      "AI and Machine Learning",     "NotebookInstance","Hrs",      0.046,    180, ["us-east-1","us-west-2"]),
    ("Amazon DynamoDB",       "Databases",                   "Table",           "WCU",      0.00065, 4500, ["us-east-1","us-west-2","eu-west-1"]),
    ("AWS Data Transfer",     "Networking",                  "DataTransfer",    "GB",       0.09,    950, ["us-east-1","us-west-2","eu-west-1"]),
    ("Amazon ElastiCache",    "Databases",                   "CacheCluster",    "Hrs",      0.068,    480, ["us-east-1","us-west-2"]),
]

AZURE_SERVICES = [
    ("Virtual Machines",         "Compute",                    "VirtualMachine",  "Hrs",    0.096,  1440, ["eastus","westeurope","southeastasia"]),
    ("Azure Blob Storage",       "Storage",                    "StorageAccount",  "GB-Mo",  0.018,   950, ["eastus","westeurope","southeastasia"]),
    ("Azure SQL Database",       "Databases",                  "SQLDatabase",     "Hrs",    0.200,   260, ["eastus","westeurope"]),
    ("Azure Kubernetes Service", "Compute",                    "ManagedCluster",  "Hrs",    0.100,   560, ["eastus","westeurope","southeastasia"]),
    ("Azure Functions",          "Compute",                    "FunctionApp",     "Req",    0.0000002, 6_000_000, ["eastus","westeurope"]),
    ("Azure Monitor",            "Management and Governance",  "Workspace",       "GB",     0.50,     70, ["eastus","westeurope"]),
    ("Azure Cosmos DB",          "Databases",                  "CosmosAccount",   "RU",     0.00008,120_000, ["eastus","westeurope","southeastasia"]),
    ("Azure Data Factory",       "Analytics",                  "Pipeline",        "Runs",   0.001,  5200, ["eastus","westeurope"]),
    ("Azure CDN",                "Networking",                 "Profile",         "GB",     0.0087, 1800, ["eastus","westeurope"]),
    ("Azure Cache for Redis",    "Databases",                  "RedisCache",      "Hrs",    0.068,   380, ["eastus","westeurope"]),
    ("Azure Machine Learning",   "AI and Machine Learning",    "Workspace",       "Hrs",    0.056,   140, ["eastus","westeurope"]),
    ("Azure Databricks",         "Analytics",                  "Workspace",       "DBU",    0.20,    320, ["eastus","westeurope"]),
]

GCP_SERVICES = [
    ("Compute Engine",       "Compute",                    "Instance",         "Hrs",    0.095,  1320, ["us-central1","us-east1","europe-west1"]),
    ("Cloud Storage",        "Storage",                    "Bucket",           "GB-Mo",  0.020,   820, ["us-central1","us-east1","europe-west1"]),
    ("Cloud SQL",            "Databases",                  "Instance",         "Hrs",    0.190,   230, ["us-central1","us-east1"]),
    ("Google Kubernetes Engine","Compute",                 "Cluster",          "Hrs",    0.100,   480, ["us-central1","us-east1","europe-west1"]),
    ("Cloud Functions",      "Compute",                    "Function",         "Req",    0.0000004, 4_000_000, ["us-central1","us-east1"]),
    ("Cloud Monitoring",     "Management and Governance",  "Workspace",        "GB",     0.25,     60, ["us-central1"]),
    ("BigQuery",             "Analytics",                  "Dataset",          "TB",     5.00,    14.5, ["us-central1","us-east1","europe-west1"]),
    ("Cloud Pub/Sub",        "Networking",                 "Topic",            "GB",     0.04,    700, ["us-central1","us-east1"]),
    ("Vertex AI",            "AI and Machine Learning",    "Endpoint",         "Hrs",    0.120,   120, ["us-central1","us-east1"]),
    ("Cloud Spanner",        "Databases",                  "Instance",         "Node-Hr",0.900,    85, ["us-central1","us-east1"]),
    ("Cloud Run",            "Compute",                    "Service",          "vCPU-s", 0.00002,320_000, ["us-central1","us-east1","europe-west1"]),
    ("Looker",               "Analytics",                  "Instance",         "Hrs",    0.180,    60, ["us-central1"]),
]

# CSP metadata
CSP_META = {
    "aws": {
        "invoice_issuer":    "Amazon Web Services",
        "publisher":         "Amazon",
        "account_id":        "aws-123456789012",
        "account_name":      "Lumen Demo AWS Account",
        "account_type":      "Management",
        "sub_prefix":        "aws-sub",
        "region_id_map": {
            "us-east-1":      "us-east-1",
            "us-west-2":      "us-west-2",
            "eu-west-1":      "eu-west-1",
        },
        "region_name_map": {
            "us-east-1":      "US East (N. Virginia)",
            "us-west-2":      "US West (Oregon)",
            "eu-west-1":      "Europe (Ireland)",
        },
    },
    "azure": {
        "invoice_issuer":    "Microsoft",
        "publisher":         "Microsoft",
        "account_id":        "azure-sub-8a2b3c4d",
        "account_name":      "Lumen Demo Azure Subscription",
        "account_type":      "Subscription",
        "sub_prefix":        "azure-rg",
        "region_id_map": {
            "eastus":         "eastus",
            "westeurope":     "westeurope",
            "southeastasia":  "southeastasia",
        },
        "region_name_map": {
            "eastus":         "East US",
            "westeurope":     "West Europe",
            "southeastasia":  "Southeast Asia",
        },
    },
    "google": {
        "invoice_issuer":    "Google",
        "publisher":         "Google",
        "account_id":        "gcp-proj-lumen-demo",
        "account_name":      "Lumen Demo GCP Project",
        "account_type":      "Project",
        "sub_prefix":        "gcp-proj",
        "region_id_map": {
            "us-central1":    "us-central1",
            "us-east1":       "us-east1",
            "europe-west1":   "europe-west1",
        },
        "region_name_map": {
            "us-central1":    "Iowa",
            "us-east1":       "South Carolina",
            "europe-west1":   "Belgium",
        },
    },
}


def _rng(d: date, csp: str) -> random.Random:
    return random.Random(int(d.strftime("%Y%m%d")) + hash(csp) % 1000)


def _make_row(
    *,
    tenant_id:    str,
    csp:          str,
    billing_date: date,
    service_name: str,
    category:     str,
    resource_type:str,
    unit:         str,
    price_per_unit: float,
    quantity:     float,
    region_id:    str,
    team:         str,
    environment:  str,
    cost_center:  str,
    rng:          random.Random,
) -> FocusCost:
    meta  = CSP_META[csp]
    cost  = round(quantity * price_per_unit * rng.uniform(0.92, 1.08), 6)
    lcost = round(cost * rng.uniform(1.0, 1.12), 6)   # list > effective

    iso_date = billing_date.isoformat()
    iso_end  = (billing_date + timedelta(days=1)).isoformat()
    region_name = meta["region_name_map"].get(region_id, region_id)

    # Derive resource ID and name
    svc_slug    = service_name.lower().replace(" ", "-").replace("(", "").replace(")", "")
    resource_id = f"/{csp}/{region_id}/{svc_slug}/{rng.randint(1000, 9999)}"

    return FocusCost(
        id                           = new_id(),
        tenant_id                    = tenant_id,
        # FOCUS required
        billing_account_id           = meta["account_id"],
        billing_account_name         = meta["account_name"],
        billing_period_start         = iso_date,
        billing_period_end           = iso_end,
        charge_period_start          = f"{iso_date}T00:00:00Z",
        charge_period_end            = f"{iso_end}T00:00:00Z",
        charge_category              = "Usage",
        invoice_issuer_name          = meta["invoice_issuer"],
        provider_name                = csp,
        publisher_name               = meta["publisher"],
        service_name                 = service_name,
        service_category             = category,
        sku_id                       = f"{csp}::{svc_slug}::{unit.lower()}",
        sku_price_id                 = f"{csp}::{svc_slug}::{unit.lower()}::od",
        region_id                    = region_id,
        region_name                  = region_name,
        resource_id                  = resource_id,
        resource_name                = f"{svc_slug}-{team}-{rng.randint(10,99)}",
        resource_type                = resource_type,
        resource_status              = "Running",
        sub_account_id               = f"{meta['sub_prefix']}-{team}",
        sub_account_name             = f"{meta['account_name']} / {team}",
        pricing_category             = "Standard",
        pricing_quantity             = round(quantity, 4),
        pricing_unit                 = unit,
        usage_quantity               = round(quantity, 4),
        usage_unit                   = unit,
        list_unit_price              = round(price_per_unit * 1.05, 8),
        list_cost                    = lcost,
        billed_cost                  = cost,
        effective_cost               = cost,
        contracted_cost              = round(cost * 0.97, 6),   # ~3% negotiated discount
        contracted_unit_price        = round(price_per_unit * 0.97, 8),
        commitment_discount_id       = "",
        commitment_discount_name     = "",
        commitment_discount_category = "",
        commitment_discount_type     = "",
        commitment_discount_status   = "",
        currency                     = "USD",
        tags                         = {
            "team": team,
            "env": environment,
            "cost_center": cost_center,
            "managed_by": "terraform",
        },
        # AI extension columns — empty for cloud infra rows
        x_ai_vendor             = "",
        x_ai_model              = "",
        x_ai_tier               = "",
        x_input_tokens          = 0.0,
        x_output_tokens         = 0.0,
        x_cache_read_tokens     = 0.0,
        x_cache_write_tokens    = 0.0,
        x_request_count         = 0,
        # FinOps chargeback
        x_team                  = team,
        x_app_id                = "",
        x_cost_center           = cost_center,
        x_environment           = environment,
    )


def seed_csp_focus_data(
    db: Session,
    tenant_id: str = "tenant-demo",
    days: int = SEED_DAYS,
    force: bool = False,
) -> dict:
    """
    Generate CSP (AWS/Azure/GCP) FOCUS v1.0 rows into focus_cost.

    Args:
        db:        SQLAlchemy session.
        tenant_id: Target tenant.
        days:      Trailing days to generate (default = SEED_DAYS / 90).
        force:     When True, delete existing CSP rows then re-seed.
                   When False (default), skip if rows already exist.
    """
    existing = (
        db.query(FocusCost)
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.x_ai_vendor == "",
            FocusCost.service_category != "",
        )
        .first()
    )

    if existing and not force:
        return {"status": "skipped", "reason": "CSP cloud data already present"}

    deleted = 0
    if existing and force:
        deleted = (
            db.query(FocusCost)
            .filter(
                FocusCost.tenant_id == tenant_id,
                FocusCost.x_ai_vendor == "",
            )
            .delete(synchronize_session=False)
        )
        db.commit()

    today     = date.today()
    start_day = today - timedelta(days=days - 1)

    rows: List[FocusCost] = []
    total = 0

    for day_offset in range(days):
        billing_date = start_day + timedelta(days=day_offset)
        is_weekend   = billing_date.weekday() >= 5
        wk_factor    = 0.60 if is_weekend else 1.0
        growth       = 1.0 + (day_offset * 0.0006)   # gentle upward trend

        for csp, services in [("aws", AWS_SERVICES), ("azure", AZURE_SERVICES), ("google", GCP_SERVICES)]:
            rng = _rng(billing_date, csp)

            for (svc_name, category, res_type, unit, price, avg_qty, regions) in services:
                # One row per service per team per day (teams are cost dimensions)
                for i, team in enumerate(TEAMS):
                    team_share = TEAM_WEIGHTS[i] * rng.uniform(0.80, 1.20)
                    qty        = avg_qty * wk_factor * growth * team_share * rng.uniform(0.85, 1.15)
                    if qty <= 0:
                        continue

                    region     = rng.choice(regions)
                    env        = rng.choices(ENVS, weights=ENV_WEIGHTS)[0]
                    cc         = rng.choice(COST_CENTERS)

                    rows.append(_make_row(
                        tenant_id     = tenant_id,
                        csp           = csp,
                        billing_date  = billing_date,
                        service_name  = svc_name,
                        category      = category,
                        resource_type = res_type,
                        unit          = unit,
                        price_per_unit = price,
                        quantity      = qty,
                        region_id     = region,
                        team          = team,
                        environment   = env,
                        cost_center   = cc,
                        rng           = rng,
                    ))

                # Flush every 8000 rows to stay memory-efficient
                if len(rows) >= 8000:
                    db.bulk_save_objects(rows)
                    db.flush()
                    total += len(rows)
                    rows = []

    if rows:
        db.bulk_save_objects(rows)
        db.flush()
        total += len(rows)

    db.commit()
    return {
        "status":   "seeded",
        "rows":     total,
        "days":     days,
        "deleted":  deleted,
        "csps":     ["aws", "azure", "google"],
    }
