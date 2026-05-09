from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TenantOut(OrmModel):
    id: str
    name: str
    status: str


class CustomerOut(OrmModel):
    id: str
    tenant_id: str
    name: str
    business_unit: str
    cost_center: str
    owner_group: str
    tags: dict[str, Any]


class ProviderConnectionOut(OrmModel):
    id: str
    tenant_id: str
    provider_id: str
    name: str
    category: str
    status: str
    credential_status: str
    signal_coverage_pct: float
    quota_remaining_pct: float
    estimated_monthly_cost: float
    last_sync_at: datetime | None
    health: dict[str, Any]


class RecommendationDefinitionOut(OrmModel):
    id: str
    name: str
    category: str
    sub_category: str
    provider_scope: str
    source_provider: str
    recommendation_type: str
    priority: str
    end_user_value: str
    implementation_complexity: str
    primary_metrics: list[Any]
    baseline_thresholds: list[Any]
    lookback_window: str
    product_catalog_dependency: str
    compatibility_group: str
    basic_engine_support: str
    notes_and_guardrails: str
    enabled: bool
    config: dict[str, Any]


class HypothesisCreate(BaseModel):
    tenant_id: str = "tenant-demo"
    definition_id: str | None = None
    name: str
    description: str = ""
    owner_group: str = "finops-admins"
    business_justification: str = ""
    category: str = "Compute"
    severity: str = "P2"
    scope: dict[str, Any] = Field(default_factory=lambda: {"providers": ["AWS", "Azure", "GCP"], "environment": "all"})
    signals: list[Any] = Field(default_factory=list)
    conditions: list[Any] = Field(default_factory=list)
    action_proposal: dict[str, Any] = Field(default_factory=dict)
    savings_model: dict[str, Any] = Field(default_factory=dict)
    risk_profile: dict[str, Any] = Field(default_factory=dict)


class HypothesisUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    owner_group: str | None = None
    business_justification: str | None = None
    category: str | None = None
    severity: str | None = None
    scope: dict[str, Any] | None = None
    signals: list[Any] | None = None
    conditions: list[Any] | None = None
    action_proposal: dict[str, Any] | None = None
    savings_model: dict[str, Any] | None = None
    risk_profile: dict[str, Any] | None = None


class HypothesisOut(OrmModel):
    id: str
    tenant_id: str
    definition_id: str | None
    name: str
    description: str
    owner_group: str
    business_justification: str
    category: str
    severity: str
    state: str
    version: int
    scope: dict[str, Any]
    signals: list[Any]
    conditions: list[Any]
    action_proposal: dict[str, Any]
    savings_model: dict[str, Any]
    risk_profile: dict[str, Any]
    last_backtest: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FindingOut(OrmModel):
    id: str
    tenant_id: str
    customer_id: str
    hypothesis_id: str | None
    definition_id: str | None
    resource_id: str
    resource_type: str
    provider: str
    account_id: str
    region: str
    state: str
    priority: str
    owner_group: str
    evidence: dict[str, Any]
    proposed_action: dict[str, Any]
    estimated_savings_monthly: float
    confidence_lower: float
    confidence_upper: float
    pricing_snapshot_id: str
    suppression_reason: str
    created_at: datetime
    updated_at: datetime


class FindingTransition(BaseModel):
    state: str
    actor: str = "system"
    reason: str = ""
    delivery_channel: str = "manual"


class ActionOut(OrmModel):
    id: str
    tenant_id: str
    finding_id: str
    action_type: str
    delivery_channel: str
    status: str
    approver_group: str
    external_ref: str
    payload: dict[str, Any]
    approved_at: datetime | None
    applied_at: datetime | None
    created_at: datetime


class OutcomeOut(OrmModel):
    id: str
    tenant_id: str
    action_id: str
    window_days: int
    status: str
    baseline_cost: float
    observed_cost: float
    estimated_savings: float
    realized_savings: float
    variance_pct: float
    evidence: dict[str, Any]
    reconciled_at: datetime | None


class ProductRateOut(OrmModel):
    id: str
    provider: str
    resource_type: str
    sku: str
    region: str
    pricing_model: str
    unit: str
    rate: float
    compatibility_group: str
    attributes: dict[str, Any]
    snapshot_id: str
    effective_at: datetime
    stale_after: datetime | None


class BacktestRequest(BaseModel):
    tenant_id: str = "tenant-demo"
    days: int = 30
    persist_findings: bool = False


class PublishRequest(BaseModel):
    target_state: str = Field(pattern="^(shadow|active|deprecated)$")
    actor: str = "system"
    override_reason: str = ""


class ImportResult(BaseModel):
    imported: int
    updated: int
    skipped: int
    path: str


class DashboardOut(BaseModel):
    totals: dict[str, Any]
    finding_states: dict[str, int]
    category_savings: list[dict[str, Any]]
    integration_health: list[dict[str, Any]]
    recent_audit_events: list[dict[str, Any]]
