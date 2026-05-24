-- ============================================================================
-- Migration 002: FOCUS v1.0 cost tables + AI cost extension tables
-- Applies on top of 001_schema.sql
-- ============================================================================

-- ── Ingest configurations ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cost_ingest_configs (
  id              text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id       text NOT NULL REFERENCES tenants(id),
  name            text NOT NULL DEFAULT 'AWS CUR',
  s3_bucket       text NOT NULL,
  s3_prefix       text NOT NULL DEFAULT '',
  aws_role_arn    text NOT NULL,
  aws_external_id text NOT NULL DEFAULT '',
  aws_region      text NOT NULL DEFAULT 'us-east-1',
  enabled         boolean NOT NULL DEFAULT true,
  last_tested_at  timestamptz,
  last_sync_at    timestamptz,
  test_status     text NOT NULL DEFAULT 'pending',
  test_message    text NOT NULL DEFAULT '',
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS azure_cost_ingest_configs (
  id                  text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id           text NOT NULL REFERENCES tenants(id),
  name                text NOT NULL DEFAULT 'Azure Cost',
  azure_tenant_id     text NOT NULL,
  client_id           text NOT NULL,
  subscription_id     text NOT NULL,
  management_group_id text NOT NULL DEFAULT '',
  enabled             boolean NOT NULL DEFAULT true,
  last_tested_at      timestamptz,
  last_sync_at        timestamptz,
  test_status         text NOT NULL DEFAULT 'pending',
  test_message        text NOT NULL DEFAULT '',
  config              jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gcp_cost_ingest_configs (
  id               text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id        text NOT NULL REFERENCES tenants(id),
  name             text NOT NULL DEFAULT 'GCP Billing',
  gcp_project_id   text NOT NULL,
  bigquery_dataset text NOT NULL,
  bigquery_table   text NOT NULL DEFAULT 'gcp_billing_export_v1',
  enabled          boolean NOT NULL DEFAULT true,
  last_tested_at   timestamptz,
  last_sync_at     timestamptz,
  test_status      text NOT NULL DEFAULT 'pending',
  test_message     text NOT NULL DEFAULT '',
  config           jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- ── Raw cost line items ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cost_details (
  id                text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id         text NOT NULL REFERENCES tenants(id),
  sourced_from      text NOT NULL DEFAULT 'cur',      -- cur | azure | gcp | manual
  account_id        text NOT NULL DEFAULT '',
  account_name      text NOT NULL DEFAULT '',
  service           text NOT NULL,
  sku               text NOT NULL DEFAULT '',
  region            text NOT NULL DEFAULT '',
  resource_id       text NOT NULL DEFAULT '',
  usage_start_date  text NOT NULL,                    -- YYYY-MM-DD
  usage_end_date    text NOT NULL DEFAULT '',
  usage_quantity    double precision NOT NULL DEFAULT 0,
  usage_unit        text NOT NULL DEFAULT '',
  unblended_cost    double precision NOT NULL DEFAULT 0,
  blended_cost      double precision NOT NULL DEFAULT 0,
  amortised_cost    double precision NOT NULL DEFAULT 0,
  list_cost         double precision NOT NULL DEFAULT 0,
  currency          text NOT NULL DEFAULT 'USD',
  tags              jsonb NOT NULL DEFAULT '{}'::jsonb,
  raw               jsonb NOT NULL DEFAULT '{}'::jsonb,
  focus_transformed boolean NOT NULL DEFAULT false,
  parsed_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, account_id, service, sku, region, usage_start_date, sourced_from)
);

-- ── FOCUS v1.0 normalized cost ───────────────────────────────────────────────
-- Column names follow FOCUS spec (snake_case). All FOCUS v1.0 required and
-- conditional columns are present. Extension columns use x_ prefix per spec.

CREATE TABLE IF NOT EXISTS focus_cost (
  id                          text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id                   text NOT NULL REFERENCES tenants(id),

  -- FOCUS Required
  billing_account_id          text NOT NULL DEFAULT '',
  billing_account_name        text NOT NULL DEFAULT '',
  billing_period_start        text NOT NULL,            -- ISO 8601 date
  billing_period_end          text NOT NULL DEFAULT '',
  charge_period_start         text NOT NULL DEFAULT '',
  charge_period_end           text NOT NULL DEFAULT '',
  charge_category             text NOT NULL DEFAULT 'Usage',
    -- CHECK: Usage | Purchase | Tax | Credit | Adjustment

  invoice_issuer_name         text NOT NULL DEFAULT '',
  provider_name               text NOT NULL DEFAULT '',
  publisher_name              text NOT NULL DEFAULT '',

  service_name                text NOT NULL DEFAULT '',
  service_category            text NOT NULL DEFAULT '',
    -- FOCUS enum: Compute | Storage | Database | Networking |
    --   AI and Machine Learning | Analytics | Security | Identity |
    --   Management and Governance | Developer Tools | Other

  sku_id                      text NOT NULL DEFAULT '',
  sku_price_id                text NOT NULL DEFAULT '',

  region_id                   text NOT NULL DEFAULT '',
  region_name                 text NOT NULL DEFAULT '',

  resource_id                 text NOT NULL DEFAULT '',
  resource_name               text NOT NULL DEFAULT '',
  resource_type               text NOT NULL DEFAULT '',
  resource_status             text NOT NULL DEFAULT '',

  sub_account_id              text NOT NULL DEFAULT '',
  sub_account_name            text NOT NULL DEFAULT '',

  pricing_category            text NOT NULL DEFAULT 'Standard',
    -- CHECK: Standard | Committed | Dynamic | Other
  pricing_quantity            double precision NOT NULL DEFAULT 0,
  pricing_unit                text NOT NULL DEFAULT '',

  usage_quantity              double precision NOT NULL DEFAULT 0,
  usage_unit                  text NOT NULL DEFAULT '',

  list_unit_price             double precision NOT NULL DEFAULT 0,
  list_cost                   double precision NOT NULL DEFAULT 0,

  -- FOCUS Conditional
  billed_cost                 double precision NOT NULL DEFAULT 0,
  effective_cost              double precision NOT NULL DEFAULT 0,
  contracted_cost             double precision NOT NULL DEFAULT 0,
  contracted_unit_price       double precision NOT NULL DEFAULT 0,

  -- Commitment discount (RI / Savings Plans / CUDs)
  commitment_discount_id       text NOT NULL DEFAULT '',
  commitment_discount_name     text NOT NULL DEFAULT '',
  commitment_discount_category text NOT NULL DEFAULT '',   -- Spend | Usage
  commitment_discount_type     text NOT NULL DEFAULT '',
  commitment_discount_status   text NOT NULL DEFAULT '',   -- Used | Unused

  currency                    text NOT NULL DEFAULT 'USD',
  tags                        jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- Extension: AI/ML metadata (x_ prefix per FOCUS spec §6 custom columns)
  x_ai_vendor                 text NOT NULL DEFAULT '',
  x_ai_model                  text NOT NULL DEFAULT '',
  x_ai_tier                   text NOT NULL DEFAULT '',   -- LLM | Embedding | Vision | TTS | STT
  x_input_tokens              double precision NOT NULL DEFAULT 0,
  x_output_tokens             double precision NOT NULL DEFAULT 0,
  x_cache_read_tokens         double precision NOT NULL DEFAULT 0,
  x_cache_write_tokens        double precision NOT NULL DEFAULT 0,
  x_request_count             integer NOT NULL DEFAULT 0,

  -- Extension: FinOps chargeback / showback
  x_team                      text NOT NULL DEFAULT '',
  x_app_id                    text NOT NULL DEFAULT '',
  x_cost_center               text NOT NULL DEFAULT '',
  x_environment               text NOT NULL DEFAULT '',

  -- Lineage
  source_detail_id            text REFERENCES cost_details(id),
  transformed_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_focus_tenant_period
  ON focus_cost (tenant_id, billing_period_start DESC);

CREATE INDEX IF NOT EXISTS idx_focus_ai
  ON focus_cost (tenant_id, x_ai_vendor, x_ai_model, billing_period_start DESC)
  WHERE x_ai_vendor != '';

CREATE INDEX IF NOT EXISTS idx_focus_service_category
  ON focus_cost (tenant_id, service_category, billing_period_start DESC);

CREATE INDEX IF NOT EXISTS idx_focus_app
  ON focus_cost (tenant_id, x_app_id, billing_period_start DESC)
  WHERE x_app_id != '';

-- ── Daily cost aggregations (dashboard cache) ─────────────────────────────────

CREATE TABLE IF NOT EXISTS cost_aggregations (
  id             text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id      text NOT NULL REFERENCES tenants(id),
  date           text NOT NULL,         -- YYYY-MM-DD
  account_id     text NOT NULL DEFAULT '',
  provider       text NOT NULL DEFAULT '',
  service        text NOT NULL,
  category       text NOT NULL DEFAULT '',
  subcategory    text NOT NULL DEFAULT '',
  region         text NOT NULL DEFAULT '',
  team           text NOT NULL DEFAULT '',
  environment    text NOT NULL DEFAULT '',
  ai_type        text NOT NULL DEFAULT '',
  ai_subtype     text NOT NULL DEFAULT '',
  total_cost     double precision NOT NULL DEFAULT 0,
  effective_cost double precision NOT NULL DEFAULT 0,
  list_cost      double precision NOT NULL DEFAULT 0,
  total_usage    double precision NOT NULL DEFAULT 0,
  unit_count     integer NOT NULL DEFAULT 0,
  resource_count integer NOT NULL DEFAULT 0,
  request_count  integer NOT NULL DEFAULT 0,
  input_tokens   double precision NOT NULL DEFAULT 0,
  output_tokens  double precision NOT NULL DEFAULT 0,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, date, account_id, service, category, region, ai_type, ai_subtype)
);

CREATE INDEX IF NOT EXISTS idx_agg_tenant_date
  ON cost_aggregations (tenant_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_agg_ai
  ON cost_aggregations (tenant_id, ai_type, ai_subtype, date DESC)
  WHERE ai_type != '';

-- ── AI Service Classification ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ai_service_classifications (
  id            text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id     text NOT NULL REFERENCES tenants(id),
  provider      text NOT NULL,          -- AWS | Azure | GCP | Anthropic | OpenAI …
  service       text NOT NULL,          -- Bedrock | Vertex | openai.com …
  sku_pattern   text NOT NULL,          -- regex matched against sku_id
  ai_type       text NOT NULL,          -- LLM | Embedding | Vision | TTS | STT
  ai_vendor     text NOT NULL,          -- Anthropic | OpenAI | Cohere …
  ai_model      text NOT NULL,          -- claude-3-5-sonnet-20241022 …
  cost_unit     text NOT NULL DEFAULT 'tokens',
  token_type    text NOT NULL DEFAULT '',    -- input_tokens | output_tokens
  price_per_1m  double precision NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider, service, sku_pattern)
);

-- ── Model router swap suggestions ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS model_swap_suggestions (
  id                    text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id             text NOT NULL REFERENCES tenants(id),
  current_model         text NOT NULL,
  current_vendor        text NOT NULL,
  suggested_model       text NOT NULL,
  suggested_vendor      text NOT NULL,
  monthly_cost_current  double precision NOT NULL DEFAULT 0,
  monthly_cost_saving   double precision NOT NULL DEFAULT 0,
  saving_pct            double precision NOT NULL DEFAULT 0,
  quality_risk          text NOT NULL DEFAULT 'Low',
  latency_delta_ms      integer NOT NULL DEFAULT 0,
  rationale             text NOT NULL DEFAULT '',
  applicable_use_cases  jsonb NOT NULL DEFAULT '[]'::jsonb,
  score                 double precision NOT NULL DEFAULT 0,
  active                boolean NOT NULL DEFAULT true,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

-- ── SaaS tool seat allocations ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS saas_tool_allocations (
  id             text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id      text NOT NULL REFERENCES tenants(id),
  tool_name      text NOT NULL,
  vendor         text NOT NULL DEFAULT '',
  user_id        text NOT NULL,
  user_email     text NOT NULL DEFAULT '',
  team           text NOT NULL DEFAULT '',
  period         text NOT NULL,          -- YYYY-MM
  seat_cost      double precision NOT NULL DEFAULT 0,
  usage_minutes  integer NOT NULL DEFAULT 0,
  completions    integer NOT NULL DEFAULT 0,
  active         boolean NOT NULL DEFAULT true,
  last_active_at timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, tool_name, user_id, period)
);

-- ── App cost attributions ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS app_cost_attributions (
  id             text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id      text NOT NULL REFERENCES tenants(id),
  app_id         text NOT NULL,
  app_name       text NOT NULL DEFAULT '',
  team           text NOT NULL DEFAULT '',
  ai_vendor      text NOT NULL,
  ai_model       text NOT NULL,
  date           text NOT NULL,           -- YYYY-MM-DD
  daily_cost     double precision NOT NULL DEFAULT 0,
  request_count  integer NOT NULL DEFAULT 0,
  input_tokens   double precision NOT NULL DEFAULT 0,
  output_tokens  double precision NOT NULL DEFAULT 0,
  avg_latency_ms integer NOT NULL DEFAULT 0,
  error_rate     double precision NOT NULL DEFAULT 0,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, app_id, ai_vendor, ai_model, date)
);

CREATE INDEX IF NOT EXISTS idx_app_attr_tenant_date
  ON app_cost_attributions (tenant_id, date DESC);

-- ── Product categories (FOCUS ServiceCategory mapping) ────────────────────────

CREATE TABLE IF NOT EXISTS product_categories (
  id           text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id    text NOT NULL REFERENCES tenants(id),
  provider     text NOT NULL,
  service_name text NOT NULL,
  sku_pattern  text NOT NULL,
  category     text NOT NULL,
  subcategory  text NOT NULL DEFAULT '',
  unit_type    text NOT NULL DEFAULT 'hour',
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider, service_name, sku_pattern)
);

-- ── Anomaly records ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS anomaly_records (
  id            text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id     text NOT NULL REFERENCES tenants(id),
  service       text NOT NULL,
  region        text NOT NULL DEFAULT '',
  account_id    text NOT NULL DEFAULT '',
  detected_date text NOT NULL,
  z_score       double precision NOT NULL DEFAULT 0,
  cost_impact   double precision NOT NULL DEFAULT 0,
  baseline_cost double precision NOT NULL DEFAULT 0,
  observed_cost double precision NOT NULL DEFAULT 0,
  detector      text NOT NULL DEFAULT 'stl',
  severity      text NOT NULL DEFAULT 'medium',
  acknowledged  boolean NOT NULL DEFAULT false,
  ack_by        text NOT NULL DEFAULT '',
  related_events jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- ── Forecast records ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS forecast_records (
  id            text PRIMARY KEY DEFAULT gen_random_uuid()::text,
  tenant_id     text NOT NULL REFERENCES tenants(id),
  service       text NOT NULL DEFAULT '__total__',
  forecast_date text NOT NULL,
  model         text NOT NULL DEFAULT 'prophet',
  scenario      text NOT NULL DEFAULT 'likely',
  forecast_cost double precision NOT NULL DEFAULT 0,
  lower_bound   double precision NOT NULL DEFAULT 0,
  upper_bound   double precision NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, service, forecast_date, model, scenario)
);
