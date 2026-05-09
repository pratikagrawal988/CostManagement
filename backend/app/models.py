from __future__ import annotations

import uuid
from datetime import datetime, timezone

from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customers: Mapped[list[Customer]] = relationship(back_populates="tenant")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_unit: Mapped[str] = mapped_column(String(120), default="Shared")
    cost_center: Mapped[str] = mapped_column(String(120), default="CC-000")
    owner_group: Mapped[str] = mapped_column(String(160), default="finops-admins")
    tags: Mapped[dict] = mapped_column(JSON, default=dict)

    tenant: Mapped[Tenant] = relationship(back_populates="customers")


class ProviderConnection(Base):
    __tablename__ = "provider_connections"
    __table_args__ = (UniqueConstraint("tenant_id", "provider_id", name="uq_provider_tenant"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider_id: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="not_configured")
    credential_status: Mapped[str] = mapped_column(String(40), default="missing")
    signal_coverage_pct: Mapped[float] = mapped_column(Float, default=0)
    quota_remaining_pct: Mapped[float] = mapped_column(Float, default=100)
    estimated_monthly_cost: Mapped[float] = mapped_column(Float, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    health: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProductRate(Base):
    __tablename__ = "product_rates"
    __table_args__ = (UniqueConstraint("provider", "resource_type", "sku", "region", "pricing_model", name="uq_product_rate"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    resource_type: Mapped[str] = mapped_column(String(80), index=True)
    sku: Mapped[str] = mapped_column(String(200), index=True)
    region: Mapped[str] = mapped_column(String(80), index=True)
    pricing_model: Mapped[str] = mapped_column(String(80), default="on_demand")
    unit: Mapped[str] = mapped_column(String(40), default="hour")
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    compatibility_group: Mapped[str] = mapped_column(String(200), index=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot_id: Mapped[str] = mapped_column(String(80), index=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationDefinition(Base):
    __tablename__ = "recommendation_definitions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    sub_category: Mapped[str] = mapped_column(String(120), default="")
    provider_scope: Mapped[str] = mapped_column(String(120), index=True)
    source_provider: Mapped[str] = mapped_column(String(300), default="")
    recommendation_type: Mapped[str] = mapped_column(String(120), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    end_user_value: Mapped[str] = mapped_column(String(80), default="")
    implementation_complexity: Mapped[str] = mapped_column(String(80), default="")
    primary_metrics: Mapped[list] = mapped_column(JSON, default=list)
    baseline_thresholds: Mapped[list] = mapped_column(JSON, default=list)
    lookback_window: Mapped[str] = mapped_column(String(40), default="14d")
    native_or_saas_data_source: Mapped[str] = mapped_column(Text, default="")
    third_party_saas_options: Mapped[list] = mapped_column(JSON, default=list)
    product_catalog_dependency: Mapped[str] = mapped_column(Text, default="")
    compatibility_group: Mapped[str] = mapped_column(String(200), default="")
    onboarding_to_engine: Mapped[str] = mapped_column(Text, default="")
    basic_engine_support: Mapped[str] = mapped_column(Text, default="")
    notes_and_guardrails: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    definition_id: Mapped[str | None] = mapped_column(ForeignKey("recommendation_definitions.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_group: Mapped[str] = mapped_column(String(160), default="finops-admins")
    business_justification: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(120), default="Compute")
    severity: Mapped[str] = mapped_column(String(40), default="P2")
    state: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    signals: Mapped[list] = mapped_column(JSON, default=list)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    action_proposal: Mapped[dict] = mapped_column(JSON, default=dict)
    savings_model: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    last_backtest: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SignalSample(Base):
    __tablename__ = "signal_samples"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    account_id: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[str] = mapped_column(String(240), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    region: Mapped[str] = mapped_column(String(80), default="")
    sku: Mapped[str] = mapped_column(String(160), default="")
    signal_name: Mapped[str] = mapped_column(String(200), index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="")
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=utcnow)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    hypothesis_id: Mapped[str | None] = mapped_column(ForeignKey("hypotheses.id"), index=True)
    definition_id: Mapped[str | None] = mapped_column(ForeignKey("recommendation_definitions.id"), index=True)
    resource_id: Mapped[str] = mapped_column(String(240), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(40))
    account_id: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(80), default="")
    state: Mapped[str] = mapped_column(String(40), default="new", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="P2")
    owner_group: Mapped[str] = mapped_column(String(160), default="finops-admins")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    proposed_action: Mapped[dict] = mapped_column(JSON, default=dict)
    estimated_savings_monthly: Mapped[float] = mapped_column(Float, default=0)
    confidence_lower: Mapped[float] = mapped_column(Float, default=0)
    confidence_upper: Mapped[float] = mapped_column(Float, default=0)
    pricing_snapshot_id: Mapped[str] = mapped_column(String(80), default="")
    suppression_reason: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(120))
    delivery_channel: Mapped[str] = mapped_column(String(80), default="manual")
    status: Mapped[str] = mapped_column(String(40), default="pending_approval")
    approver_group: Mapped[str] = mapped_column(String(160), default="finops-admins")
    external_ref: Mapped[str] = mapped_column(String(200), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    action_id: Mapped[str] = mapped_column(ForeignKey("actions.id"), index=True)
    window_days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    baseline_cost: Mapped[float] = mapped_column(Float, default=0)
    observed_cost: Mapped[float] = mapped_column(Float, default=0)
    estimated_savings: Mapped[float] = mapped_column(Float, default=0)
    realized_savings: Mapped[float] = mapped_column(Float, default=0)
    variance_pct: Mapped[float] = mapped_column(Float, default=0)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    actor: Mapped[str] = mapped_column(String(160), default="system")
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="platform")
    job_name: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


# Cost Aggregation Models

class CostIngestConfig(Base):
    """Admin configuration for AWS CUR ingestion"""
    __tablename__ = "cost_ingest_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_prefix: Mapped[str] = mapped_column(String(500), default="AWSLogs")
    aws_role_arn: Mapped[str] = mapped_column(String(500), nullable=False)
    aws_external_id: Mapped[str] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[str] = mapped_column(String(40), default="pending")
    test_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AzureCostIngestConfig(Base):
    """Admin configuration for Azure Cost Management ingestion"""
    __tablename__ = "azure_cost_ingest_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    azure_subscription_id: Mapped[str] = mapped_column(String(36), nullable=False)  # GUID format
    azure_tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)  # Azure AD tenant
    client_id: Mapped[str] = mapped_column(String(36), nullable=False)  # Service Principal app ID
    client_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted client secret
    export_scope: Mapped[str] = mapped_column(String(500), default="/subscriptions/{subscription_id}")
    export_frequency: Mapped[str] = mapped_column(String(50), default="Daily")  # Daily or Monthly
    data_source: Mapped[str] = mapped_column(String(100), default="actual_cost")  # actual_cost or amortized_cost
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[str] = mapped_column(String(40), default="pending")
    test_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class GcpCostIngestConfig(Base):
    """Admin configuration for GCP BigQuery cost ingestion"""
    __tablename__ = "gcp_cost_ingest_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    gcp_project_id: Mapped[str] = mapped_column(String(255), nullable=False)  # GCP project ID
    service_account_email: Mapped[str] = mapped_column(String(255), nullable=False)  # SA email
    service_account_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted JSON key
    billing_account_id: Mapped[str] = mapped_column(String(20), nullable=False)  # Billing account ID
    bq_dataset_id: Mapped[str] = mapped_column(String(255), default="billing_export")  # BigQuery dataset
    bq_table_id: Mapped[str] = mapped_column(String(255), default="gcp_billing_export_v1")  # BigQuery table
    export_frequency: Mapped[str] = mapped_column(String(50), default="Daily")  # Daily or Monthly
    data_source: Mapped[str] = mapped_column(String(100), default="standard")  # standard or detailed
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[str] = mapped_column(String(40), default="pending")
    test_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CostDetail(Base):
    """Raw AWS CUR data (native format)"""
    __tablename__ = "cost_details"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "service", "sku", "region", "usage_start_date", name="uq_cost_detail"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    service: Mapped[str] = mapped_column(String(100), index=True, default="")
    service_code: Mapped[str] = mapped_column(String(100), default="")
    sku: Mapped[str] = mapped_column(String(500), index=True, default="")
    region: Mapped[str] = mapped_column(String(50), index=True, default="")
    usage_type: Mapped[str] = mapped_column(String(500), default="")
    usage_start_date: Mapped[str | None] = mapped_column(String(20), index=True)  # YYYY-MM-DD
    usage_end_date: Mapped[str | None] = mapped_column(String(20))
    usage_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    cost_before_discount: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    cost_after_discount: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    cost_with_tax: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    cost_allocation_tags: Mapped[dict] = mapped_column(JSON, default=dict)
    resource_id: Mapped[str] = mapped_column(String(500), default="")
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    sourced_from: Mapped[str] = mapped_column(String(50), default="cur")  # cur, focus_export
    cur_date: Mapped[str | None] = mapped_column(String(20))  # YYYY-MM-DD
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FocusCost(Base):
    """FOCUS-normalized cost data"""
    __tablename__ = "focus_costs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "service_name", "sku", "region", "billing_period_start", name="uq_focus_cost"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    billing_period_start: Mapped[str] = mapped_column(String(20), index=True)  # YYYY-MM-DD
    invoice_issuer: Mapped[str] = mapped_column(String(50), index=True)  # aws, azure, gcp
    service_name: Mapped[str] = mapped_column(String(100), index=True, default="")
    service_category: Mapped[str] = mapped_column(String(100), index=True, default="")
    sku: Mapped[str] = mapped_column(String(500), index=True, default="")
    region: Mapped[str] = mapped_column(String(50), index=True, default="")
    usage_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    usage_unit: Mapped[str] = mapped_column(String(50), default="")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    billed_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    resource_id: Mapped[str] = mapped_column(String(500), default="")
    cost_category: Mapped[str] = mapped_column(String(100), default="")
    chargeback_entity: Mapped[str] = mapped_column(String(255), default="")
    synth_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProductCategory(Base):
    """Normalizes service/SKU to standard categories across CSPs"""
    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "service_name", "sku_pattern", name="uq_product_category"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), index=True)  # AWS, AZURE, GCP
    service_name: Mapped[str] = mapped_column(String(100), index=True)
    sku_pattern: Mapped[str] = mapped_column(String(500))  # regex pattern for matching SKUs
    category: Mapped[str] = mapped_column(String(100), index=True)  # Compute, Storage, Database, etc.
    subcategory: Mapped[str] = mapped_column(String(100), index=True)  # EC2, RDS, S3, etc.
    unit_type: Mapped[str] = mapped_column(String(50))  # hour, gb_month, gb_transfer, request
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AIServiceClassification(Base):
    """Maps AI SKUs to service + model + tier classification"""
    __tablename__ = "ai_service_classifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "sku_pattern", "tier", name="uq_ai_service"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(20), index=True)  # AWS, AZURE, GCP
    service_name: Mapped[str] = mapped_column(String(100), index=True)  # Bedrock, SageMaker, VertexAI
    sku_pattern: Mapped[str] = mapped_column(String(500))  # regex pattern
    ai_type: Mapped[str] = mapped_column(String(100), index=True)  # LLM, Vision, Embeddings, Search, Speech
    ai_subtype: Mapped[str] = mapped_column(String(100), index=True)  # Claude, Llama, Mistral, GPT, Gemini
    model_variant: Mapped[str] = mapped_column(String(100))  # 3-Sonnet, 3-Opus, 4-Turbo, etc.
    usage_unit: Mapped[str] = mapped_column(String(50))  # tokens, calls, minutes
    tier: Mapped[str] = mapped_column(String(100), index=True)  # input_tokens, output_tokens, cache_read, per_request
    cost_allocation_group: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CostAggregation(Base):
    """Pre-computed daily aggregations for dashboard performance"""
    __tablename__ = "cost_aggregations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "account_id", "date", "service", "category", "region", name="uq_cost_aggregation"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    date: Mapped[str] = mapped_column(String(20), index=True)  # YYYY-MM-DD
    service: Mapped[str] = mapped_column(String(100), index=True, default="")
    category: Mapped[str] = mapped_column(String(100), index=True, default="")
    subcategory: Mapped[str] = mapped_column(String(100), default="")
    ai_type: Mapped[str] = mapped_column(String(100), index=True, default="")
    ai_subtype: Mapped[str] = mapped_column(String(100), default="")
    region: Mapped[str] = mapped_column(String(50), index=True, default="")
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    total_usage: Mapped[Decimal] = mapped_column(Numeric(20, 10), default=0)
    unit_count: Mapped[int] = mapped_column(Integer, default=0)
    resource_count: Mapped[int] = mapped_column(Integer, default=0)
    aggregated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
