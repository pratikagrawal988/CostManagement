const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8088";

export type Dashboard = {
  totals: Record<string, number | string>;
  finding_states: Record<string, number>;
  category_savings: Array<{ category: string; savings: number }>;
  integration_health: Array<Record<string, string | number>>;
  recent_audit_events: Array<Record<string, string>>;
};

export type RecommendationDefinition = {
  id: string;
  name: string;
  category: string;
  sub_category: string;
  provider_scope: string;
  source_provider: string;
  recommendation_type: string;
  priority: string;
  end_user_value: string;
  implementation_complexity: string;
  primary_metrics: string[];
  baseline_thresholds: Array<Record<string, string | number | boolean>>;
  lookback_window: string;
  product_catalog_dependency: string;
  compatibility_group: string;
  basic_engine_support: string;
  notes_and_guardrails: string;
  enabled: boolean;
  config: Record<string, unknown>;
};

export type Hypothesis = {
  id: string;
  tenant_id: string;
  definition_id: string | null;
  name: string;
  description: string;
  owner_group: string;
  business_justification: string;
  category: string;
  severity: string;
  state: string;
  version: number;
  scope: Record<string, unknown>;
  signals: unknown[];
  conditions: unknown[];
  action_proposal: Record<string, unknown>;
  savings_model: Record<string, unknown>;
  risk_profile: Record<string, unknown>;
  last_backtest: Record<string, unknown>;
};

export type Finding = {
  id: string;
  customer_id: string;
  hypothesis_id: string | null;
  definition_id: string | null;
  resource_id: string;
  resource_type: string;
  provider: string;
  state: string;
  priority: string;
  owner_group: string;
  evidence: Record<string, unknown>;
  proposed_action: Record<string, unknown>;
  estimated_savings_monthly: number;
  confidence_lower: number;
  confidence_upper: number;
  pricing_snapshot_id: string;
};

export type ProductRate = {
  id: string;
  provider: string;
  resource_type: string;
  sku: string;
  region: string;
  pricing_model: string;
  unit: string;
  rate: number;
  compatibility_group: string;
  snapshot_id: string;
};

export type Integration = {
  id: string;
  provider_id: string;
  name: string;
  category: string;
  status: string;
  credential_status: string;
  signal_coverage_pct: number;
  quota_remaining_pct: number;
  estimated_monthly_cost: number;
  last_sync_at: string | null;
  health: Record<string, unknown>;
};

export type Customer = {
  id: string;
  name: string;
  business_unit: string;
  cost_center: string;
  owner_group: string;
  tags: Record<string, string>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Record<string, unknown>>("/health"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  customers: () => request<Customer[]>("/api/customers"),
  definitions: (query = "") => request<RecommendationDefinition[]>(`/api/recommendation-definitions${query}`),
  instantiate: (id: string) => request<Hypothesis>(`/api/recommendation-definitions/${id}/instantiate`, { method: "POST" }),
  evaluateDefinition: (id: string) => request<Record<string, unknown>>(`/api/recommendation-definitions/${id}/evaluate`, { method: "POST" }),
  hypotheses: () => request<Hypothesis[]>("/api/hypotheses"),
  backtest: (id: string) => request<Record<string, unknown>>(`/api/hypotheses/${id}/backtest`, { method: "POST", body: JSON.stringify({ days: 30 }) }),
  publish: (id: string, target_state: string) =>
    request<Hypothesis>(`/api/hypotheses/${id}/publish`, { method: "POST", body: JSON.stringify({ target_state, actor: "finops-admin", override_reason: "Demo approval" }) }),
  findings: (query = "") => request<Finding[]>(`/api/findings${query}`),
  transitionFinding: (id: string, state: string) =>
    request<Finding>(`/api/findings/${id}/transition`, { method: "POST", body: JSON.stringify({ state, actor: "finops-admin", delivery_channel: "manual" }) }),
  actions: () => request<Array<Record<string, unknown>>>("/api/actions"),
  applyAction: (id: string) => request<Record<string, unknown>>(`/api/actions/${id}/apply`, { method: "POST" }),
  outcomes: () => request<Array<Record<string, unknown>>>("/api/outcomes"),
  productCatalog: (query = "") => request<ProductRate[]>(`/api/product-catalog${query}`),
  integrations: () => request<Integration[]>("/api/integrations"),
  manifests: () => request<Array<Record<string, unknown>>>("/api/integrations/manifests"),
  syncIntegrations: () => request<Integration[]>("/api/integrations/sync", { method: "POST" }),
  runIngestion: () => request<Record<string, unknown>>("/api/ingestion/run", { method: "POST" }),
  runEvaluator: () => request<Record<string, unknown>>("/api/evaluate/run", { method: "POST" }),
  runReconciler: () => request<Record<string, unknown>>("/api/reconciler/run", { method: "POST" }),
  jobs: () => request<Record<string, unknown>>("/api/jobs"),
  customerRecommendations: (id: string) => request<Record<string, unknown>>(`/api/customers/${id}/recommendations`),
};
