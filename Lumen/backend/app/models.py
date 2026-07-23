"""
SQLAlchemy ORM models for the FinOps Recommendation Engine.

Table groups:
  Auth              — User, RefreshToken
  Core tenancy      — Tenant, Customer
  Provider infra    — ProviderConnection, CostIngestConfig, AzureCostIngestConfig, GcpCostIngestConfig
  Raw cost          — CostDetail
  FOCUS normalized  — FocusCost  (FOCUS v1.0 compliant + x_ extension columns)
  Aggregations      — CostAggregation
  AI cost           — AIServiceClassification, AIVendorCost, AIModelCost,
                       ModelSwapSuggestion, SaaSToolAllocation, AppCostAttribution
  Pricing           — ProductRate, ProductCategory
  Recommendations   — RecommendationDefinition, Hypothesis, Finding, Action, Outcome
  Observability     — SignalSample, AnomalyRecord, ForecastRecord
  Platform          — JobRun, AuditEvent
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, Double, Float, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from .database import Base


# ── Helpers ───────────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_aware(dt: datetime | None) -> datetime | None:
    """Normalize to a tz-aware (UTC) datetime.

    SQLite doesn't preserve timezone info even for ``DateTime(timezone=True)``
    columns, so values round-tripped through it come back naive, while
    Postgres (production) round-trips them tz-aware already. Assume naive ==
    UTC (all writes in this codebase go through ``utcnow()``) so comparisons
    against a fresh ``datetime.now(timezone.utc)`` never raise "can't compare
    offset-naive and offset-aware datetimes" depending on which DB backend
    happens to be behind the session.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


# ── Auth ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)

    id              = Column(String, primary_key=True, default=new_id)
    tenant_id       = Column(String, ForeignKey("tenants.id"), nullable=False)
    email           = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, nullable=False, default="")
    role            = Column(String, nullable=False, default="analyst")   # admin|analyst|viewer
    is_active       = Column(Boolean, nullable=False, default=True)
    last_login_at   = Column(DateTime(timezone=True))
    created_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    refresh_tokens  = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id          = Column(String, primary_key=True, default=new_id)
    user_id     = Column(String, ForeignKey("users.id"), nullable=False)
    tenant_id   = Column(String, nullable=False)
    token_hash  = Column(String, nullable=False, unique=True)
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    revoked     = Column(Boolean, nullable=False, default=False)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="refresh_tokens")


# ── Core Tenancy ──────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"

    id         = Column(String, primary_key=True)
    name       = Column(String, nullable=False)
    status     = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    customers          = relationship("Customer",           back_populates="tenant")
    provider_conns     = relationship("ProviderConnection", back_populates="tenant")
    ingest_configs     = relationship("CostIngestConfig",   back_populates="tenant")
    azure_configs      = relationship("AzureCostIngestConfig", back_populates="tenant")
    gcp_configs        = relationship("GcpCostIngestConfig",   back_populates="tenant")


class Customer(Base):
    __tablename__ = "customers"

    id            = Column(String, primary_key=True)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    name          = Column(String, nullable=False)
    business_unit = Column(String, nullable=False, default="Shared")
    cost_center   = Column(String, nullable=False, default="CC-000")
    owner_group   = Column(String, nullable=False, default="finops-admins")
    tags          = Column(JSON,   nullable=False, default=dict)

    tenant = relationship("Tenant", back_populates="customers")


# ── Provider Connections ──────────────────────────────────────────────────────

class ProviderConnection(Base):
    """Registry of configured provider integrations (one row per provider per tenant)."""
    __tablename__ = "provider_connections"
    __table_args__ = (UniqueConstraint("tenant_id", "provider_id"),)

    id                    = Column(String, primary_key=True, default=new_id)
    tenant_id             = Column(String, ForeignKey("tenants.id"), nullable=False)
    provider_id           = Column(String, nullable=False)           # e.g. "aws", "azure", "datadog"
    name                  = Column(String, nullable=False)
    category              = Column(String, nullable=False)           # Cloud, Observability, ITSM …
    status                = Column(String, nullable=False, default="not_configured")
    credential_status     = Column(String, nullable=False, default="missing")
    signal_coverage_pct   = Column(Double, nullable=False, default=0.0)
    quota_remaining_pct   = Column(Double, nullable=False, default=100.0)
    estimated_monthly_cost= Column(Double, nullable=False, default=0.0)
    last_sync_at          = Column(DateTime(timezone=True))
    config                = Column(JSON, nullable=False, default=dict)
    health                = Column(JSON, nullable=False, default=dict)
    created_at            = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at            = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="provider_conns")


# ── Ingest Configurations ──────────────────────────────────────────────────────

class CostIngestConfig(Base):
    """AWS CUR ingestion configuration — one row per S3 bucket / role ARN pair."""
    __tablename__ = "cost_ingest_configs"

    id              = Column(String, primary_key=True, default=new_id)
    tenant_id       = Column(String, ForeignKey("tenants.id"), nullable=False)
    name            = Column(String, nullable=False, default="AWS CUR")
    s3_bucket       = Column(String, nullable=False)
    s3_prefix       = Column(String, nullable=False, default="")
    aws_role_arn    = Column(String, nullable=False)
    aws_external_id = Column(String, nullable=False, default="")
    aws_region      = Column(String, nullable=False, default="us-east-1")
    enabled         = Column(Boolean, nullable=False, default=True)
    last_tested_at  = Column(DateTime(timezone=True))
    last_sync_at    = Column(DateTime(timezone=True))
    test_status     = Column(String, nullable=False, default="pending")  # pending|ok|error
    test_message    = Column(Text, nullable=False, default="")
    created_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="ingest_configs")


class AzureCostIngestConfig(Base):
    """Azure Cost Management export configuration."""
    __tablename__ = "azure_cost_ingest_configs"

    id                  = Column(String, primary_key=True, default=new_id)
    tenant_id           = Column(String, ForeignKey("tenants.id"), nullable=False)
    name                = Column(String, nullable=False, default="Azure Cost")
    azure_tenant_id     = Column(String, nullable=False)       # AAD tenant
    client_id           = Column(String, nullable=False)
    # client_secret stored encrypted in config JSON — never as plaintext column
    subscription_id     = Column(String, nullable=False)
    management_group_id = Column(String, nullable=False, default="")
    enabled             = Column(Boolean, nullable=False, default=True)
    last_tested_at      = Column(DateTime(timezone=True))
    last_sync_at        = Column(DateTime(timezone=True))
    test_status         = Column(String, nullable=False, default="pending")
    test_message        = Column(Text, nullable=False, default="")
    config              = Column(JSON, nullable=False, default=dict)  # encrypted secret here
    created_at          = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at          = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="azure_configs")


class GcpCostIngestConfig(Base):
    """GCP Billing export → BigQuery configuration."""
    __tablename__ = "gcp_cost_ingest_configs"

    id                    = Column(String, primary_key=True, default=new_id)
    tenant_id             = Column(String, ForeignKey("tenants.id"), nullable=False)
    name                  = Column(String, nullable=False, default="GCP Billing")
    gcp_project_id        = Column(String, nullable=False)
    bigquery_dataset      = Column(String, nullable=False)
    bigquery_table        = Column(String, nullable=False, default="gcp_billing_export_v1")
    # service account JSON stored encrypted in config JSON
    enabled               = Column(Boolean, nullable=False, default=True)
    last_tested_at        = Column(DateTime(timezone=True))
    last_sync_at          = Column(DateTime(timezone=True))
    test_status           = Column(String, nullable=False, default="pending")
    test_message          = Column(Text, nullable=False, default="")
    config                = Column(JSON, nullable=False, default=dict)
    created_at            = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at            = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant", back_populates="gcp_configs")


# ── Raw Cost (pre-normalisation) ──────────────────────────────────────────────

class CostDetail(Base):
    """
    Raw cost line items as ingested from provider sources (CUR, Azure export, GCP BQ).
    One row per resource/SKU/day before FOCUS normalisation.
    """
    __tablename__ = "cost_details"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "service", "sku", "region", "usage_start_date", "sourced_from"),
    )

    id               = Column(String, primary_key=True, default=new_id)
    tenant_id        = Column(String, ForeignKey("tenants.id"), nullable=False)
    sourced_from     = Column(String, nullable=False, default="cur")   # cur | azure | gcp | manual
    account_id       = Column(String, nullable=False, default="")
    account_name     = Column(String, nullable=False, default="")
    service          = Column(String, nullable=False)
    sku              = Column(String, nullable=False, default="")
    region           = Column(String, nullable=False, default="")
    resource_id      = Column(String, nullable=False, default="")
    usage_start_date = Column(String, nullable=False)                  # YYYY-MM-DD
    usage_end_date   = Column(String, nullable=False, default="")
    usage_quantity   = Column(Double,  nullable=False, default=0.0)
    usage_unit       = Column(String, nullable=False, default="")
    unblended_cost   = Column(Double,  nullable=False, default=0.0)
    blended_cost     = Column(Double,  nullable=False, default=0.0)
    amortised_cost   = Column(Double,  nullable=False, default=0.0)
    list_cost        = Column(Double,  nullable=False, default=0.0)
    currency         = Column(String, nullable=False, default="USD")
    tags             = Column(JSON,   nullable=False, default=dict)
    raw              = Column(JSON,   nullable=False, default=dict)    # original row for auditability
    focus_transformed= Column(Boolean, nullable=False, default=False)
    parsed_at        = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── FOCUS v1.0 Normalized Cost ────────────────────────────────────────────────

class FocusCost(Base):
    """
    FOCUS v1.0 normalized cost rows.

    Column names match the FOCUS spec exactly (snake_case mapping of PascalCase spec names).
    Reference: https://focus.finops.org/specification/

    Required columns per FOCUS v1.0:
      BillingAccountId, BillingAccountName, BillingPeriodEnd, BillingPeriodStart,
      ChargeCategory, ChargePeriodEnd, ChargePeriodStart, InvoiceIssuerName,
      ListCost, ListUnitPrice, PricingCategory, PricingQuantity, PricingUnit,
      ProviderName, PublisherName, RegionId, RegionName, ResourceId,
      ResourceName, ResourceType, ServiceCategory, ServiceName, SkuId, SkuPriceId,
      SubAccountId, SubAccountName, Tags, UsageQuantity, UsageUnit

    Conditional:
      BilledCost, EffectiveCost, ContractedCost, ContractedUnitPrice,
      CommitmentDiscount*, ResourceStatus

    Extension (x_ prefix):
      x_ai_vendor, x_ai_model, x_ai_tier, x_input_tokens, x_output_tokens,
      x_cache_read_tokens, x_team, x_app_id, x_cost_center, x_environment
    """
    __tablename__ = "focus_cost"

    id = Column(String, primary_key=True, default=new_id)

    # ── Tenancy ────────────────────────────────────────────────────────────────
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)

    # ── FOCUS Required ────────────────────────────────────────────────────────
    billing_account_id       = Column(String, nullable=False, default="")
    billing_account_name     = Column(String, nullable=False, default="")
    billing_period_start     = Column(String, nullable=False)   # ISO 8601 date
    billing_period_end       = Column(String, nullable=False, default="")
    charge_period_start      = Column(String, nullable=False, default="")  # ISO 8601 datetime
    charge_period_end        = Column(String, nullable=False, default="")
    charge_category          = Column(String, nullable=False, default="Usage")
    # ChargeCategory enum: Usage | Purchase | Tax | Credit | Adjustment

    invoice_issuer_name      = Column(String, nullable=False, default="")  # e.g. "Amazon Web Services"
    provider_name            = Column(String, nullable=False, default="")  # e.g. "AWS"
    publisher_name           = Column(String, nullable=False, default="")  # e.g. "Amazon"

    service_name             = Column(String, nullable=False, default="")
    service_category         = Column(String, nullable=False, default="")
    # ServiceCategory enum: Compute | Storage | Database | Networking | AI and Machine Learning |
    #   Analytics | Security | Identity | Management and Governance | Developer Tools | Other

    sku_id                   = Column(String, nullable=False, default="")
    sku_price_id             = Column(String, nullable=False, default="")

    region_id                = Column(String, nullable=False, default="")
    region_name              = Column(String, nullable=False, default="")

    resource_id              = Column(String, nullable=False, default="")
    resource_name            = Column(String, nullable=False, default="")
    resource_type            = Column(String, nullable=False, default="")
    resource_status          = Column(String, nullable=False, default="")  # Running | Stopped | etc.

    sub_account_id           = Column(String, nullable=False, default="")
    sub_account_name         = Column(String, nullable=False, default="")

    pricing_category         = Column(String, nullable=False, default="Standard")
    # PricingCategory enum: Standard | Committed | Dynamic | Other
    pricing_quantity         = Column(Double, nullable=False, default=0.0)
    pricing_unit             = Column(String, nullable=False, default="")

    usage_quantity           = Column(Double, nullable=False, default=0.0)
    usage_unit               = Column(String, nullable=False, default="")

    list_unit_price          = Column(Double, nullable=False, default=0.0)
    list_cost                = Column(Double, nullable=False, default=0.0)

    # ── FOCUS Conditional ─────────────────────────────────────────────────────
    billed_cost              = Column(Double, nullable=False, default=0.0)
    effective_cost           = Column(Double, nullable=False, default=0.0)
    contracted_cost          = Column(Double, nullable=False, default=0.0)
    contracted_unit_price    = Column(Double, nullable=False, default=0.0)

    # Commitment discount (RI / Savings Plans / CUDs)
    commitment_discount_id       = Column(String, nullable=False, default="")
    commitment_discount_name     = Column(String, nullable=False, default="")
    commitment_discount_category = Column(String, nullable=False, default="")  # Spend | Usage
    commitment_discount_type     = Column(String, nullable=False, default="")  # e.g. "Reserved Instance"
    commitment_discount_status   = Column(String, nullable=False, default="")  # Used | Unused

    currency                 = Column(String, nullable=False, default="USD")
    tags                     = Column(JSON, nullable=False, default=dict)

    # ── Extension: AI/ML metadata (x_ prefix per FOCUS spec) ─────────────────
    x_ai_vendor              = Column(String, nullable=False, default="")   # Anthropic, OpenAI …
    x_ai_model               = Column(String, nullable=False, default="")   # claude-3-5-sonnet …
    x_ai_tier                = Column(String, nullable=False, default="")   # LLM, Embedding, Vision …
    x_input_tokens           = Column(Double, nullable=False, default=0.0)
    x_output_tokens          = Column(Double, nullable=False, default=0.0)
    x_cache_read_tokens      = Column(Double, nullable=False, default=0.0)
    x_cache_write_tokens     = Column(Double, nullable=False, default=0.0)
    x_request_count          = Column(Integer, nullable=False, default=0)

    # ── Extension: FinOps chargeback / showback ────────────────────────────────
    x_team                   = Column(String, nullable=False, default="")
    x_app_id                 = Column(String, nullable=False, default="")
    x_cost_center            = Column(String, nullable=False, default="")
    x_environment            = Column(String, nullable=False, default="")   # prod | staging | dev

    # ── Lineage ────────────────────────────────────────────────────────────────
    source_detail_id         = Column(String, ForeignKey("cost_details.id"))
    transformed_at           = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    tenant = relationship("Tenant")


# ── Daily Aggregations (dashboard performance cache) ──────────────────────────

class CostAggregation(Base):
    """
    Pre-computed daily rollup per service/category/region.
    Rebuilt by the focus_transform job; used directly by dashboard APIs.
    """
    __tablename__ = "cost_aggregations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "date", "account_id", "service", "category", "region", "ai_type", "ai_subtype"),
    )

    id             = Column(String, primary_key=True, default=new_id)
    tenant_id      = Column(String, ForeignKey("tenants.id"), nullable=False)
    date           = Column(String, nullable=False)               # YYYY-MM-DD
    account_id     = Column(String, nullable=False, default="")
    provider       = Column(String, nullable=False, default="")
    service        = Column(String, nullable=False)
    category       = Column(String, nullable=False, default="")
    subcategory    = Column(String, nullable=False, default="")
    region         = Column(String, nullable=False, default="")
    team           = Column(String, nullable=False, default="")
    environment    = Column(String, nullable=False, default="")
    ai_type        = Column(String, nullable=False, default="")   # LLM | Embedding | Vision …
    ai_subtype     = Column(String, nullable=False, default="")   # Claude | GPT-4 | Gemini …
    total_cost     = Column(Double, nullable=False, default=0.0)
    effective_cost = Column(Double, nullable=False, default=0.0)
    list_cost      = Column(Double, nullable=False, default=0.0)
    total_usage    = Column(Double, nullable=False, default=0.0)
    unit_count     = Column(Integer, nullable=False, default=0)
    resource_count = Column(Integer, nullable=False, default=0)
    request_count  = Column(Integer, nullable=False, default=0)
    input_tokens   = Column(Double, nullable=False, default=0.0)
    output_tokens  = Column(Double, nullable=False, default=0.0)
    created_at     = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at     = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


# ── AI Cost Models ────────────────────────────────────────────────────────────

class AIServiceClassification(Base):
    """
    Maps provider SKU patterns to AI vendor/model/tier metadata.
    Used during FOCUS transform to populate x_ai_* extension columns.
    """
    __tablename__ = "ai_service_classifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "service", "sku_pattern"),
    )

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    provider      = Column(String, nullable=False)          # AWS | Azure | GCP | Anthropic …
    service       = Column(String, nullable=False)          # Bedrock | OpenAI | Vertex …
    sku_pattern   = Column(String, nullable=False)          # regex
    ai_type       = Column(String, nullable=False)          # LLM | Embedding | Vision | TTS | STT
    ai_vendor     = Column(String, nullable=False)          # Anthropic | OpenAI | Cohere …
    ai_model      = Column(String, nullable=False)          # claude-3-5-sonnet | gpt-4o …
    cost_unit     = Column(String, nullable=False, default="tokens")  # tokens | requests | hour
    token_type    = Column(String, nullable=False, default="")   # input_tokens | output_tokens
    price_per_1m  = Column(Double, nullable=False, default=0.0)  # USD per 1M tokens
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class ModelSwapSuggestion(Base):
    """AI model router swap suggestions — cheaper alternatives with quality/latency trade-off."""
    __tablename__ = "model_swap_suggestions"

    id                   = Column(String, primary_key=True, default=new_id)
    tenant_id            = Column(String, ForeignKey("tenants.id"), nullable=False)
    current_model        = Column(String, nullable=False)
    current_vendor       = Column(String, nullable=False)
    suggested_model      = Column(String, nullable=False)
    suggested_vendor     = Column(String, nullable=False)
    monthly_cost_current = Column(Double, nullable=False, default=0.0)
    monthly_cost_saving  = Column(Double, nullable=False, default=0.0)
    saving_pct           = Column(Double, nullable=False, default=0.0)
    quality_risk         = Column(String, nullable=False, default="Low")    # Low | Medium | High
    latency_delta_ms     = Column(Integer, nullable=False, default=0)       # positive = slower
    rationale            = Column(Text, nullable=False, default="")
    applicable_use_cases = Column(JSON, nullable=False, default=list)
    score                = Column(Double, nullable=False, default=0.0)       # 0–1 confidence
    active               = Column(Boolean, nullable=False, default=True)
    created_at           = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at           = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class SaaSToolAllocation(Base):
    """
    Per-seat / per-user allocation for AI SaaS tools (Cursor, GitHub Copilot, etc.).
    One row per tool per user per billing period.
    """
    __tablename__ = "saas_tool_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "tool_name", "user_id", "period"),
    )

    id              = Column(String, primary_key=True, default=new_id)
    tenant_id       = Column(String, ForeignKey("tenants.id"), nullable=False)
    tool_name       = Column(String, nullable=False)   # Cursor | GitHub Copilot | JetBrains AI …
    vendor          = Column(String, nullable=False, default="")
    user_id         = Column(String, nullable=False)
    user_email      = Column(String, nullable=False, default="")
    team            = Column(String, nullable=False, default="")
    period          = Column(String, nullable=False)   # YYYY-MM
    seat_cost       = Column(Double, nullable=False, default=0.0)
    usage_minutes   = Column(Integer, nullable=False, default=0)
    completions     = Column(Integer, nullable=False, default=0)
    active          = Column(Boolean, nullable=False, default=True)
    last_active_at  = Column(DateTime(timezone=True))
    created_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class AppCostAttribution(Base):
    """
    Cost per API caller / application (app_id dimension).
    Populated from request logs tagged with x-app-id headers or SDK metadata.
    """
    __tablename__ = "app_cost_attributions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "app_id", "ai_vendor", "ai_model", "date"),
    )

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    app_id        = Column(String, nullable=False)
    app_name      = Column(String, nullable=False, default="")
    team          = Column(String, nullable=False, default="")
    ai_vendor     = Column(String, nullable=False)
    ai_model      = Column(String, nullable=False)
    date          = Column(String, nullable=False)   # YYYY-MM-DD
    daily_cost    = Column(Double, nullable=False, default=0.0)
    request_count = Column(Integer, nullable=False, default=0)
    input_tokens  = Column(Double, nullable=False, default=0.0)
    output_tokens = Column(Double, nullable=False, default=0.0)
    avg_latency_ms= Column(Integer, nullable=False, default=0)
    error_rate    = Column(Double, nullable=False, default=0.0)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── Pricing Reference ─────────────────────────────────────────────────────────

class ProductRate(Base):
    """Provider pricing rates — ingested from AWS Pricing API, Azure Retail Prices, GCP SKU catalog."""
    __tablename__ = "product_rates"
    __table_args__ = (
        UniqueConstraint("provider", "resource_type", "sku", "region", "pricing_model"),
    )

    id                  = Column(String, primary_key=True, default=new_id)
    provider            = Column(String, nullable=False)
    resource_type       = Column(String, nullable=False)
    sku                 = Column(String, nullable=False)
    region              = Column(String, nullable=False)
    pricing_model       = Column(String, nullable=False, default="on_demand")
    unit                = Column(String, nullable=False, default="hour")
    rate                = Column(Double, nullable=False)
    compatibility_group = Column(String, nullable=False)
    attributes          = Column(JSON, nullable=False, default=dict)
    snapshot_id         = Column(String, nullable=False)
    effective_at        = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    stale_after         = Column(DateTime(timezone=True))


class ProductCategory(Base):
    """Maps provider service + SKU pattern to FOCUS ServiceCategory + subcategory."""
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "service_name", "sku_pattern"),
    )

    id           = Column(String, primary_key=True, default=new_id)
    tenant_id    = Column(String, ForeignKey("tenants.id"), nullable=False)
    provider     = Column(String, nullable=False)
    service_name = Column(String, nullable=False)
    sku_pattern  = Column(String, nullable=False)   # regex
    category     = Column(String, nullable=False)   # FOCUS ServiceCategory value
    subcategory  = Column(String, nullable=False, default="")
    unit_type    = Column(String, nullable=False, default="hour")
    created_at   = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── Recommendations ───────────────────────────────────────────────────────────

class RecommendationDefinition(Base):
    __tablename__ = "recommendation_definitions"

    id                         = Column(String, primary_key=True)
    name                       = Column(String, nullable=False)
    category                   = Column(String, nullable=False)
    sub_category               = Column(String, nullable=False, default="")
    provider_scope             = Column(String, nullable=False)
    source_provider            = Column(String, nullable=False, default="")
    recommendation_type        = Column(String, nullable=False)
    priority                   = Column(String, nullable=False)
    end_user_value             = Column(Text, nullable=False, default="")
    implementation_complexity  = Column(String, nullable=False, default="")
    primary_metrics            = Column(JSON, nullable=False, default=list)
    baseline_thresholds        = Column(JSON, nullable=False, default=list)
    lookback_window            = Column(String, nullable=False, default="14d")
    native_or_saas_data_source = Column(String, nullable=False, default="")
    third_party_saas_options   = Column(JSON, nullable=False, default=list)
    product_catalog_dependency = Column(String, nullable=False, default="")
    compatibility_group        = Column(String, nullable=False, default="")
    onboarding_to_engine       = Column(String, nullable=False, default="")
    basic_engine_support       = Column(String, nullable=False, default="")
    notes_and_guardrails       = Column(Text, nullable=False, default="")
    enabled                    = Column(Boolean, nullable=False, default=True)
    config                     = Column(JSON, nullable=False, default=dict)
    imported_at                = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id                   = Column(String, primary_key=True, default=new_id)
    tenant_id            = Column(String, ForeignKey("tenants.id"), nullable=False)
    definition_id        = Column(String, ForeignKey("recommendation_definitions.id"))
    name                 = Column(String, nullable=False)
    description          = Column(Text, nullable=False, default="")
    owner_group          = Column(String, nullable=False, default="finops-admins")
    business_justification = Column(Text, nullable=False, default="")
    category             = Column(String, nullable=False, default="Compute")
    severity             = Column(String, nullable=False, default="P2")
    state                = Column(String, nullable=False, default="draft")
    version              = Column(Integer, nullable=False, default=1)
    scope                = Column(JSON, nullable=False, default=dict)
    signals              = Column(JSON, nullable=False, default=list)
    conditions           = Column(JSON, nullable=False, default=list)
    action_proposal      = Column(JSON, nullable=False, default=dict)
    savings_model        = Column(JSON, nullable=False, default=dict)
    risk_profile         = Column(JSON, nullable=False, default=dict)
    last_backtest        = Column(JSON, nullable=False, default=dict)
    created_at           = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at           = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Finding(Base):
    __tablename__ = "findings"

    id                        = Column(String, primary_key=True, default=new_id)
    tenant_id                 = Column(String, ForeignKey("tenants.id"), nullable=False)
    customer_id               = Column(String, ForeignKey("customers.id"), nullable=False)
    hypothesis_id             = Column(String, ForeignKey("hypotheses.id"))
    definition_id             = Column(String, ForeignKey("recommendation_definitions.id"))
    resource_id               = Column(String, nullable=False)
    resource_type             = Column(String, nullable=False)
    provider                  = Column(String, nullable=False)
    account_id                = Column(String, nullable=False, default="")
    region                    = Column(String, nullable=False, default="")
    state                     = Column(String, nullable=False, default="new")
    priority                  = Column(String, nullable=False, default="P2")
    owner_group               = Column(String, nullable=False, default="finops-admins")
    evidence                  = Column(JSON, nullable=False, default=dict)
    proposed_action           = Column(JSON, nullable=False, default=dict)
    estimated_savings_monthly = Column(Double, nullable=False, default=0.0)
    confidence_lower          = Column(Double, nullable=False, default=0.0)
    confidence_upper          = Column(Double, nullable=False, default=0.0)
    pricing_snapshot_id       = Column(String, nullable=False, default="")
    suppression_reason        = Column(String, nullable=False, default="")
    created_at                = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at                = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Action(Base):
    __tablename__ = "actions"

    id               = Column(String, primary_key=True, default=new_id)
    tenant_id        = Column(String, ForeignKey("tenants.id"), nullable=False)
    finding_id       = Column(String, ForeignKey("findings.id"), nullable=False)
    action_type      = Column(String, nullable=False)
    delivery_channel = Column(String, nullable=False, default="manual")
    status           = Column(String, nullable=False, default="pending_approval")
    approver_group   = Column(String, nullable=False, default="finops-admins")
    external_ref     = Column(String, nullable=False, default="")
    payload          = Column(JSON, nullable=False, default=dict)
    approved_at      = Column(DateTime(timezone=True))
    applied_at       = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at       = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Outcome(Base):
    __tablename__ = "outcomes"
    __table_args__ = (UniqueConstraint("action_id", "window_days"),)

    id                = Column(String, primary_key=True, default=new_id)
    tenant_id         = Column(String, ForeignKey("tenants.id"), nullable=False)
    action_id         = Column(String, ForeignKey("actions.id"), nullable=False)
    window_days       = Column(Integer, nullable=False)
    status            = Column(String, nullable=False, default="pending")
    baseline_cost     = Column(Double, nullable=False, default=0.0)
    observed_cost     = Column(Double, nullable=False, default=0.0)
    estimated_savings = Column(Double, nullable=False, default=0.0)
    realized_savings  = Column(Double, nullable=False, default=0.0)
    variance_pct      = Column(Double, nullable=False, default=0.0)
    evidence          = Column(JSON, nullable=False, default=dict)
    reconciled_at     = Column(DateTime(timezone=True))
    created_at        = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── Observability ─────────────────────────────────────────────────────────────

class SignalSample(Base):
    __tablename__ = "signal_samples"

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    customer_id   = Column(String, ForeignKey("customers.id"), nullable=False)
    provider      = Column(String, nullable=False)
    account_id    = Column(String, nullable=False)
    resource_id   = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    region        = Column(String, nullable=False, default="")
    sku           = Column(String, nullable=False, default="")
    signal_name   = Column(String, nullable=False)
    value         = Column(Double, nullable=False)
    unit          = Column(String, nullable=False, default="")
    sampled_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    dimensions    = Column(JSON, nullable=False, default=dict)


class AnomalyRecord(Base):
    """Detected anomalies from STL/ML ensemble job."""
    __tablename__ = "anomaly_records"

    id              = Column(String, primary_key=True, default=new_id)
    tenant_id       = Column(String, ForeignKey("tenants.id"), nullable=False)
    service         = Column(String, nullable=False)
    region          = Column(String, nullable=False, default="")
    account_id      = Column(String, nullable=False, default="")
    detected_date   = Column(String, nullable=False)   # YYYY-MM-DD
    z_score         = Column(Double, nullable=False, default=0.0)
    cost_impact     = Column(Double, nullable=False, default=0.0)
    baseline_cost   = Column(Double, nullable=False, default=0.0)
    observed_cost   = Column(Double, nullable=False, default=0.0)
    detector        = Column(String, nullable=False, default="stl")  # stl | ml | both
    severity        = Column(String, nullable=False, default="medium")
    acknowledged    = Column(Boolean, nullable=False, default=False)
    ack_by          = Column(String, nullable=False, default="")
    related_events  = Column(JSON, nullable=False, default=list)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class ForecastRecord(Base):
    """Forecast data points generated by Prophet/Holt-Winters/ARIMA jobs."""
    __tablename__ = "forecast_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "service", "forecast_date", "model", "scenario"),
    )

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    service       = Column(String, nullable=False, default="__total__")
    forecast_date = Column(String, nullable=False)   # YYYY-MM-DD
    model         = Column(String, nullable=False, default="prophet")  # prophet | holt_winters | arima
    scenario      = Column(String, nullable=False, default="likely")   # best | likely | worst
    forecast_cost = Column(Double, nullable=False, default=0.0)
    lower_bound   = Column(Double, nullable=False, default=0.0)
    upper_bound   = Column(Double, nullable=False, default=0.0)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── Platform ──────────────────────────────────────────────────────────────────

class JobRun(Base):
    __tablename__ = "job_runs"

    id                 = Column(String, primary_key=True, default=new_id)
    tenant_id          = Column(String, nullable=False, default="platform")
    job_name           = Column(String, nullable=False)
    status             = Column(String, nullable=False, default="running")
    started_at         = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    finished_at        = Column(DateTime(timezone=True))
    records_processed  = Column(Integer, nullable=False, default=0)
    details            = Column(JSON, nullable=False, default=dict)


class Budget(Base):
    """Budget definition with optional scope filters; actuals computed from FocusCost."""
    __tablename__ = "budgets"

    id               = Column(String, primary_key=True, default=new_id)
    tenant_id        = Column(String, ForeignKey("tenants.id"), nullable=False)
    name             = Column(String, nullable=False)
    amount           = Column(Double, nullable=False)
    period           = Column(String, nullable=False, default="monthly")  # monthly|quarterly|annual
    currency         = Column(String, nullable=False, default="USD")
    # Scope filters — empty string means "all"
    provider_name    = Column(String, nullable=False, default="")
    service_category = Column(String, nullable=False, default="")
    sub_account_id   = Column(String, nullable=False, default="")
    alert_thresholds = Column(JSON,   nullable=False, default=list)       # e.g. [80, 100] (% of amount)
    owner_email      = Column(String, nullable=False, default="")
    enabled          = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at       = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class NotificationChannel(Base):
    """Delivery target for alerts: Slack incoming webhook or email address."""
    __tablename__ = "notification_channels"

    id         = Column(String, primary_key=True, default=new_id)
    tenant_id  = Column(String, ForeignKey("tenants.id"), nullable=False)
    type       = Column(String, nullable=False)                 # slack | email
    name       = Column(String, nullable=False, default="")
    target     = Column(String, nullable=False)                 # webhook URL / email address
    enabled    = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class AlertNotification(Base):
    """Record of a sent budget alert — one row per (budget, threshold, period)."""
    __tablename__ = "alert_notifications"
    __table_args__ = (UniqueConstraint("budget_id", "threshold", "period_start"),)

    id              = Column(String, primary_key=True, default=new_id)
    tenant_id       = Column(String, ForeignKey("tenants.id"), nullable=False)
    budget_id       = Column(String, ForeignKey("budgets.id"), nullable=False)
    threshold       = Column(Double, nullable=False)
    period_start    = Column(String, nullable=False)
    utilization_pct = Column(Double, nullable=False, default=0.0)
    message         = Column(Text,   nullable=False, default="")
    results         = Column(JSON,   nullable=False, default=list)  # per-channel send outcomes
    created_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── Tag Management ────────────────────────────────────────────────────────────

class TagPolicy(Base):
    """
    Tenant-wide tag governance policy: which keys are required/recommended,
    and (optionally) which values are allowed for each.

    required_keys: list of
      {"key": "Team", "level": "required"|"recommended", "description": "...",
       "allowed_values": ["platform", "data-eng", ...]}   # empty list = any value
    """
    __tablename__ = "tag_policies"
    __table_args__ = (UniqueConstraint("tenant_id"),)

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    required_keys = Column(JSON, nullable=False, default=list)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class TagKeyAlias(Base):
    """Maps an inconsistent raw tag key (e.g. 'squad', 'team-name', 'TEAM') to
    the canonical key ('Team') it should be normalized to."""
    __tablename__ = "tag_key_aliases"
    __table_args__ = (UniqueConstraint("tenant_id", "alias_key"),)

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    canonical_key = Column(String, nullable=False)
    alias_key     = Column(String, nullable=False)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class TagValueAlias(Base):
    """Maps an inconsistent raw tag value (e.g. 'Production', 'PROD') to the
    canonical value ('production') for a given canonical tag key."""
    __tablename__ = "tag_value_aliases"
    __table_args__ = (UniqueConstraint("tenant_id", "tag_key", "alias_value"),)

    id              = Column(String, primary_key=True, default=new_id)
    tenant_id       = Column(String, ForeignKey("tenants.id"), nullable=False)
    tag_key         = Column(String, nullable=False)   # canonical key
    canonical_value = Column(String, nullable=False)
    alias_value     = Column(String, nullable=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class TagPrediction(Base):
    """
    A suggested value for a tag key missing on a resource, generated by a
    heuristic (sibling-resource majority vote, account-level default, or
    resource-id naming pattern). Reviewed and approved/rejected by a user;
    approval writes a ResourceTagOverride.
    """
    __tablename__ = "tag_predictions"
    __table_args__ = (UniqueConstraint("tenant_id", "resource_id", "tag_key"),)

    id               = Column(String, primary_key=True, default=new_id)
    tenant_id        = Column(String, ForeignKey("tenants.id"), nullable=False)
    resource_id      = Column(String, nullable=False)
    resource_name    = Column(String, nullable=False, default="")
    provider         = Column(String, nullable=False, default="")
    service          = Column(String, nullable=False, default="")
    tag_key          = Column(String, nullable=False)
    predicted_value  = Column(String, nullable=False)
    confidence       = Column(Double, nullable=False, default=0.0)   # 0.0–1.0
    method           = Column(String, nullable=False, default="")    # sibling_majority | account_default | naming_pattern
    evidence         = Column(JSON, nullable=False, default=dict)
    status           = Column(String, nullable=False, default="pending")  # pending|approved|rejected|applied
    created_at       = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at      = Column(DateTime(timezone=True))


class ResourceTagOverride(Base):
    """
    Final applied tag value for a resource — from an approved prediction, a
    normalization bulk-apply, or a manual edit. Layered on top of raw tags
    at read time (resource inventory) and consulted during FOCUS transform
    so future ingested cost rows for the same resource pick it up too.
    """
    __tablename__ = "resource_tag_overrides"
    __table_args__ = (UniqueConstraint("tenant_id", "resource_id", "tag_key"),)

    id          = Column(String, primary_key=True, default=new_id)
    tenant_id   = Column(String, ForeignKey("tenants.id"), nullable=False)
    resource_id = Column(String, nullable=False)
    tag_key     = Column(String, nullable=False)
    tag_value   = Column(String, nullable=False)
    source      = Column(String, nullable=False, default="manual")  # manual|predicted|normalized
    applied_at  = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ── Databricks (platform-layer cost, distinct from CSP infra cost) ───────────
#
# Databricks bills DBUs (Databricks Units) for the platform layer SEPARATELY
# from what the underlying cloud provider bills for the VMs/storage Databricks
# provisions on your behalf. These models capture that platform-layer cost;
# reconciliation with the CSP infra cost happens by joining on cluster_id
# against FocusCost rows tagged with tags["DatabricksClusterId"] (the EC2/VM
# instances that back the cluster) — see routes_databricks.py.

class DatabricksCluster(Base):
    """Cluster/warehouse inventory — one row per cluster or SQL warehouse."""
    __tablename__ = "databricks_clusters"
    __table_args__ = (UniqueConstraint("tenant_id", "cluster_id"),)

    id                = Column(String, primary_key=True, default=new_id)
    tenant_id         = Column(String, ForeignKey("tenants.id"), nullable=False)
    cluster_id        = Column(String, nullable=False)
    cluster_name      = Column(String, nullable=False, default="")
    workspace_id      = Column(String, nullable=False, default="")
    workspace_name    = Column(String, nullable=False, default="")
    cloud_provider    = Column(String, nullable=False, default="AWS")   # AWS | Azure | GCP
    region            = Column(String, nullable=False, default="")
    cluster_type      = Column(String, nullable=False, default="all_purpose")  # all_purpose | job | sql_warehouse | dlt
    node_type_id      = Column(String, nullable=False, default="")
    num_workers       = Column(Integer, nullable=False, default=0)
    tags              = Column(JSON, nullable=False, default=dict)     # team, cost_center, project
    auto_terminate    = Column(Boolean, nullable=False, default=True)
    created_at        = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class DatabricksUsageRecord(Base):
    """
    Daily DBU consumption per cluster/SKU — the Databricks platform-fee layer.
    Mirrors system.billing.usage semantics (sku_name, usage_quantity, date).
    """
    __tablename__ = "databricks_usage_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cluster_id", "sku_name", "usage_date"),
    )

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    cluster_id    = Column(String, nullable=False)
    workspace_id  = Column(String, nullable=False, default="")
    sku_name      = Column(String, nullable=False)      # STANDARD_ALL_PURPOSE_COMPUTE | STANDARD_JOBS_COMPUTE | STANDARD_SQL_COMPUTE | PREMIUM_JOBS_COMPUTE | DLT_CORE_COMPUTE
    usage_date    = Column(String, nullable=False)       # YYYY-MM-DD
    dbu_quantity  = Column(Double, nullable=False, default=0.0)
    dbu_unit_price= Column(Double, nullable=False, default=0.0)   # $ per DBU
    dbu_cost      = Column(Double, nullable=False, default=0.0)
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class DatabricksJobRun(Base):
    """One row per job/pipeline run — cost, duration, and outcome."""
    __tablename__ = "databricks_job_runs"

    id            = Column(String, primary_key=True, default=new_id)
    tenant_id     = Column(String, ForeignKey("tenants.id"), nullable=False)
    job_id        = Column(String, nullable=False)
    job_name      = Column(String, nullable=False, default="")
    run_id        = Column(String, nullable=False)
    cluster_id    = Column(String, nullable=False, default="")
    workspace_id  = Column(String, nullable=False, default="")
    run_type      = Column(String, nullable=False, default="scheduled")  # scheduled | manual | retry
    status        = Column(String, nullable=False, default="success")   # success | failed | cancelled | running
    start_time    = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    duration_seconds = Column(Integer, nullable=False, default=0)
    dbu_cost      = Column(Double, nullable=False, default=0.0)
    tags          = Column(JSON, nullable=False, default=dict)   # team, pipeline_owner
    created_at    = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class DatabricksClusterUtilization(Base):
    """Daily utilization/idle snapshot per cluster — the optimization lever."""
    __tablename__ = "databricks_cluster_utilization"
    __table_args__ = (UniqueConstraint("tenant_id", "cluster_id", "date"),)

    id                    = Column(String, primary_key=True, default=new_id)
    tenant_id             = Column(String, ForeignKey("tenants.id"), nullable=False)
    cluster_id            = Column(String, nullable=False)
    date                  = Column(String, nullable=False)   # YYYY-MM-DD
    avg_cpu_utilization_pct   = Column(Double, nullable=False, default=0.0)
    avg_memory_utilization_pct= Column(Double, nullable=False, default=0.0)
    active_hours          = Column(Double, nullable=False, default=0.0)
    idle_hours            = Column(Double, nullable=False, default=0.0)
    idle_cost             = Column(Double, nullable=False, default=0.0)  # DBU cost attributable to idle hours


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id          = Column(String, primary_key=True, default=new_id)
    tenant_id   = Column(String, ForeignKey("tenants.id"), nullable=False)
    actor       = Column(String, nullable=False, default="system")
    entity_type = Column(String, nullable=False)
    entity_id   = Column(String, nullable=False)
    event_type  = Column(String, nullable=False)
    payload     = Column(JSON, nullable=False, default=dict)
    created_at  = Column(DateTime(timezone=True), nullable=False, default=utcnow)
