CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS tenants (
  id text PRIMARY KEY,
  name text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customers (
  id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES tenants(id),
  name text NOT NULL,
  business_unit text NOT NULL DEFAULT 'Shared',
  cost_center text NOT NULL DEFAULT 'CC-000',
  owner_group text NOT NULL DEFAULT 'finops-admins',
  tags jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS provider_connections (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  provider_id text NOT NULL,
  name text NOT NULL,
  category text NOT NULL,
  status text NOT NULL DEFAULT 'not_configured',
  credential_status text NOT NULL DEFAULT 'missing',
  signal_coverage_pct double precision NOT NULL DEFAULT 0,
  quota_remaining_pct double precision NOT NULL DEFAULT 100,
  estimated_monthly_cost double precision NOT NULL DEFAULT 0,
  last_sync_at timestamptz,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  health jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider_id)
);

CREATE TABLE IF NOT EXISTS product_rates (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  provider text NOT NULL,
  resource_type text NOT NULL,
  sku text NOT NULL,
  region text NOT NULL,
  pricing_model text NOT NULL DEFAULT 'on_demand',
  unit text NOT NULL DEFAULT 'hour',
  rate double precision NOT NULL,
  compatibility_group text NOT NULL,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb,
  snapshot_id text NOT NULL,
  effective_at timestamptz NOT NULL DEFAULT now(),
  stale_after timestamptz,
  UNIQUE (provider, resource_type, sku, region, pricing_model)
);

CREATE TABLE IF NOT EXISTS recommendation_definitions (
  id text PRIMARY KEY,
  name text NOT NULL,
  category text NOT NULL,
  sub_category text NOT NULL DEFAULT '',
  provider_scope text NOT NULL,
  source_provider text NOT NULL DEFAULT '',
  recommendation_type text NOT NULL,
  priority text NOT NULL,
  end_user_value text NOT NULL DEFAULT '',
  implementation_complexity text NOT NULL DEFAULT '',
  primary_metrics jsonb NOT NULL DEFAULT '[]'::jsonb,
  baseline_thresholds jsonb NOT NULL DEFAULT '[]'::jsonb,
  lookback_window text NOT NULL DEFAULT '14d',
  native_or_saas_data_source text NOT NULL DEFAULT '',
  third_party_saas_options jsonb NOT NULL DEFAULT '[]'::jsonb,
  product_catalog_dependency text NOT NULL DEFAULT '',
  compatibility_group text NOT NULL DEFAULT '',
  onboarding_to_engine text NOT NULL DEFAULT '',
  basic_engine_support text NOT NULL DEFAULT '',
  notes_and_guardrails text NOT NULL DEFAULT '',
  enabled boolean NOT NULL DEFAULT true,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  imported_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hypotheses (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  definition_id text REFERENCES recommendation_definitions(id),
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  owner_group text NOT NULL DEFAULT 'finops-admins',
  business_justification text NOT NULL DEFAULT '',
  category text NOT NULL DEFAULT 'Compute',
  severity text NOT NULL DEFAULT 'P2',
  state text NOT NULL DEFAULT 'draft',
  version integer NOT NULL DEFAULT 1,
  scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  signals jsonb NOT NULL DEFAULT '[]'::jsonb,
  conditions jsonb NOT NULL DEFAULT '[]'::jsonb,
  action_proposal jsonb NOT NULL DEFAULT '{}'::jsonb,
  savings_model jsonb NOT NULL DEFAULT '{}'::jsonb,
  risk_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_backtest jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_samples (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  customer_id text NOT NULL REFERENCES customers(id),
  provider text NOT NULL,
  account_id text NOT NULL,
  resource_id text NOT NULL,
  resource_type text NOT NULL,
  region text NOT NULL DEFAULT '',
  sku text NOT NULL DEFAULT '',
  signal_name text NOT NULL,
  value double precision NOT NULL,
  unit text NOT NULL DEFAULT '',
  sampled_at timestamptz NOT NULL DEFAULT now(),
  dimensions jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS findings (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  customer_id text NOT NULL REFERENCES customers(id),
  hypothesis_id text REFERENCES hypotheses(id),
  definition_id text REFERENCES recommendation_definitions(id),
  resource_id text NOT NULL,
  resource_type text NOT NULL,
  provider text NOT NULL,
  account_id text NOT NULL DEFAULT '',
  region text NOT NULL DEFAULT '',
  state text NOT NULL DEFAULT 'new',
  priority text NOT NULL DEFAULT 'P2',
  owner_group text NOT NULL DEFAULT 'finops-admins',
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  proposed_action jsonb NOT NULL DEFAULT '{}'::jsonb,
  estimated_savings_monthly double precision NOT NULL DEFAULT 0,
  confidence_lower double precision NOT NULL DEFAULT 0,
  confidence_upper double precision NOT NULL DEFAULT 0,
  pricing_snapshot_id text NOT NULL DEFAULT '',
  suppression_reason text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS actions (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  finding_id text NOT NULL REFERENCES findings(id),
  action_type text NOT NULL,
  delivery_channel text NOT NULL DEFAULT 'manual',
  status text NOT NULL DEFAULT 'pending_approval',
  approver_group text NOT NULL DEFAULT 'finops-admins',
  external_ref text NOT NULL DEFAULT '',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  approved_at timestamptz,
  applied_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outcomes (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  action_id text NOT NULL REFERENCES actions(id),
  window_days integer NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  baseline_cost double precision NOT NULL DEFAULT 0,
  observed_cost double precision NOT NULL DEFAULT 0,
  estimated_savings double precision NOT NULL DEFAULT 0,
  realized_savings double precision NOT NULL DEFAULT 0,
  variance_pct double precision NOT NULL DEFAULT 0,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  reconciled_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (action_id, window_days)
);

CREATE TABLE IF NOT EXISTS audit_events (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL REFERENCES tenants(id),
  actor text NOT NULL DEFAULT 'system',
  entity_type text NOT NULL,
  entity_id text NOT NULL,
  event_type text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_runs (
  id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id text NOT NULL DEFAULT 'platform',
  job_name text NOT NULL,
  status text NOT NULL DEFAULT 'running',
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  records_processed integer NOT NULL DEFAULT 0,
  details jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_findings_tenant_state ON findings (tenant_id, state);
CREATE INDEX IF NOT EXISTS idx_findings_customer ON findings (tenant_id, customer_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_tenant_state ON hypotheses (tenant_id, state);
CREATE INDEX IF NOT EXISTS idx_signal_samples_resource ON signal_samples (tenant_id, resource_id, signal_name, sampled_at DESC);
CREATE INDEX IF NOT EXISTS idx_definitions_category_priority ON recommendation_definitions (category, priority);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events (entity_type, entity_id, created_at DESC);
