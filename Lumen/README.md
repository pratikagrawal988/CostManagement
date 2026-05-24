<<<<<<< HEAD
# FinOps Recommendation Engine

Self-contained production-style implementation of the FinOps Recommendation Engine. It includes a FastAPI backend, PostgreSQL schema, seeded recommendation catalog import, deterministic evaluator/backtest pipeline, provider registry, scheduled ingestion jobs, and a React console for recommendations and findings.

## What Is Included

- Backend API for tenants, customers, integrations, recommendation definitions, hypotheses, backtests, findings, actions, outcomes, audits, schedules, and dashboard rollups.
- PostgreSQL DDL in `db/init/001_schema.sql` plus SQLAlchemy models for application runtime.
- Config-driven recommendation import from `config/recommendations/basic-recommendation-catalog-global.csv`.
- Provider manifests for AWS, Azure, GCP, Kubernetes, Product Catalog, Datadog, Kubecost, Jira, ServiceNow, Slack, Teams, and AI/GPU aggregate telemetry sources.
- Scheduled jobs for metric ingestion, billing ingestion, pricing refresh, native recommendation import, evaluator runs, and realized-savings reconciliation.
- Frontend console with Dashboard, Recommendations, Production Monitor, Connection Health, Aggregation Engine, Failure Analysis, Product Catalog, Global Rec Library, Basic Readiness, Integrations, Batch Simulation, and Customer Advisories.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Frontend: `http://127.0.0.1:5174`
- Backend API: `http://127.0.0.1:8088/docs`

The app seeds a demo tenant and customers on startup. If real provider credentials are not configured, connectors run deterministic sample ingestion so the full workflow is usable locally.

## Live Integration Model

Integrations are declared in `config/provider_registry.yaml`. Credentials should be passed through environment variables or a secret manager in deployment. The connector layer is designed so each provider can:

1. Run a health probe.
2. Estimate ingestion cost/volume.
3. Pull metrics or billing rows on its configured interval.
4. Normalize data into the Signal Catalog.
5. Import CSP-native or SaaS recommendations as normalized findings.

## Recommendation Config Model

Recommendations are live when they are imported into the database with `enabled=true`. To add or update recommendations:

1. Add rows to a CSV with the same columns as `basic-recommendation-catalog-global.csv`.
2. POST it to `/api/recommendation-definitions/import`, or restart the backend with `SEED_ON_STARTUP=true`.
3. The evaluator compiles `primary_metrics`, `baseline_thresholds`, `lookback_window`, and `recommendation_type` into deterministic findings.

## Deployment Notes

- Use PostgreSQL in every shared environment.
- Set `CORS_ORIGINS` to the hosted frontend origin.
- Configure provider credentials via secrets; do not commit credentials.
- Run scheduler workers as a separate service if evaluation volume grows beyond one process.
- Use the event log as the audit source of truth; finding/action/outcome state is a projection.
=======
# CloudOptimization
>>>>>>> origin/main
