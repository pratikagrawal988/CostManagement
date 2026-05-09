# FinOps SaaS - Project Restructuring Plan

**Status:** Ready for Implementation  
**Date:** May 9, 2026

## Current Structure (❌ Non-Standard)

```
FinOps/
└── Recommendation-engine/
    ├── backend/
    │   ├── app/
    │   │   ├── models.py
    │   │   ├── main.py
    │   │   ├── jobs.py
    │   │   ├── azure_jobs.py
    │   │   ├── gcp_jobs.py
    │   │   ├── routes_cost.py
    │   │   ├── routes_azure.py
    │   │   ├── routes_gcp.py
    │   │   ├── seed_cost_mappings.py
    │   │   └── ...
    │   ├── tests/
    │   ├── requirements.txt
    │   └── ...
    ├── frontend/
    │   ├── src/
    │   │   ├── pages/
    │   │   │   ├── CostDashboards.jsx
    │   │   │   └── AdminCostSetup.jsx
    │   │   └── ...
    │   └── ...
    ├── config/
    │   └── schedules.yaml
    └── docker-compose.yml
```

**Issues:**
- Backend buried inside Recommendation-engine folder
- No clear separation of concerns
- No proper API layer organization (all routes in one folder)
- Frontend components not organized by feature
- No infrastructure-as-code folder
- No clear documentation structure
- Monolithic jobs in one directory

---

## Target Structure (✅ Enterprise Standard)

```
finops-saas/
│
├── backend/                          # Backend API (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── settings.py               # Configuration
│   │   ├── database.py               # Database connection
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   ├── schemas.py                # Pydantic schemas
│   │   │
│   │   ├── api/                      # API routes organized by resource
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cost/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── routes.py     # GET/POST /api/v1/cost/*
│   │   │   │   │   ├── schemas.py
│   │   │   │   │   └── service.py    # Business logic
│   │   │   │   ├── aws/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── routes.py     # GET/POST /api/v1/aws/*
│   │   │   │   │   ├── schemas.py
│   │   │   │   │   └── service.py
│   │   │   │   ├── azure/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── routes.py     # GET/POST /api/v1/azure/*
│   │   │   │   │   ├── schemas.py
│   │   │   │   │   └── service.py
│   │   │   │   ├── gcp/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── routes.py     # GET/POST /api/v1/gcp/*
│   │   │   │   │   ├── schemas.py
│   │   │   │   │   └── service.py
│   │   │   │   ├── users/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── routes.py     # User management
│   │   │   │   │   ├── schemas.py
│   │   │   │   │   └── service.py
│   │   │   │   ├── health/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── routes.py     # Health checks
│   │   │   │   └── __init__.py       # Register all routers
│   │   │   └── README.md
│   │   │
│   │   ├── jobs/                     # Background jobs & scheduling
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py          # APScheduler setup
│   │   │   ├── aws/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cur_ingest.py
│   │   │   │   └── focus_transform.py
│   │   │   ├── azure/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cost_api_ingest.py
│   │   │   │   └── focus_transform.py
│   │   │   ├── gcp/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── bigquery_ingest.py
│   │   │   │   └── focus_transform.py
│   │   │   ├── shared/
│   │   │   │   ├── __init__.py
│   │   │   │   └── focus_transform.py  # Shared transform logic
│   │   │   └── README.md
│   │   │
│   │   ├── services/                 # Business logic & orchestration
│   │   │   ├── __init__.py
│   │   │   ├── cost_service.py       # Cost aggregation logic
│   │   │   ├── recommendation_service.py
│   │   │   ├── auth_service.py       # RBAC & authentication
│   │   │   ├── budget_service.py
│   │   │   └── ai_service.py
│   │   │
│   │   ├── connectors/               # Cloud provider SDKs
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Abstract base class
│   │   │   ├── aws/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── s3_connector.py
│   │   │   │   ├── curparquet_parser.py
│   │   │   │   └── sts_connector.py
│   │   │   ├── azure/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cost_api_connector.py
│   │   │   │   └── auth_connector.py
│   │   │   ├── gcp/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── bigquery_connector.py
│   │   │   │   └── auth_connector.py
│   │   │   └── README.md
│   │   │
│   │   ├── seed/                     # Data seeding & migrations
│   │   │   ├── __init__.py
│   │   │   ├── seed_data.py
│   │   │   ├── mappings/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── aws_mappings.py
│   │   │   │   ├── azure_mappings.py
│   │   │   │   └── gcp_mappings.py
│   │   │   └── README.md
│   │   │
│   │   ├── middleware/               # Custom middleware
│   │   │   ├── __init__.py
│   │   │   ├── rbac.py               # RBAC enforcement
│   │   │   ├── logging.py
│   │   │   └── error_handling.py
│   │   │
│   │   ├── utils/                    # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── decorators.py
│   │   │   ├── constants.py
│   │   │   └── exceptions.py
│   │   │
│   │   └── README.md
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py               # Pytest fixtures
│   │   ├── unit/
│   │   │   ├── test_cost_service.py
│   │   │   ├── test_aws_connector.py
│   │   │   ├── test_azure_connector.py
│   │   │   └── test_gcp_connector.py
│   │   ├── integration/
│   │   │   ├── test_cost_api.py
│   │   │   ├── test_aws_ingest.py
│   │   │   ├── test_azure_ingest.py
│   │   │   └── test_gcp_ingest.py
│   │   ├── fixtures/
│   │   │   ├── aws_fixtures.py
│   │   │   ├── azure_fixtures.py
│   │   │   └── gcp_fixtures.py
│   │   └── README.md
│   │
│   ├── migrations/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       ├── 002_add_azure_config.py
│   │       └── 003_add_gcp_config.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── .env.example
│   ├── pytest.ini
│   ├── setup.py
│   └── README.md
│
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/
│   │   │   │   ├── Executive/
│   │   │   │   │   ├── ExecutiveSummary.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── Finance/
│   │   │   │   │   ├── FinancePortal.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── FinOps/
│   │   │   │   │   ├── FinOpsAnalytics.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── Team/
│   │   │   │   │   ├── TeamDashboard.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── Cloud/
│   │   │   │   │   ├── AWSDashboard.jsx
│   │   │   │   │   ├── AzureDashboard.jsx
│   │   │   │   │   ├── GCPDashboard.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── Focus/
│   │   │   │   │   ├── FocusNormalizedDashboard.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── AI/
│   │   │   │   │   ├── AICostDashboard.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── DashboardRouter.jsx
│   │   │   │   └── index.ts
│   │   │   ├── Admin/
│   │   │   │   ├── CostSetup/
│   │   │   │   │   ├── AwsSetup.jsx
│   │   │   │   │   ├── AzureSetup.jsx
│   │   │   │   │   ├── GcpSetup.jsx
│   │   │   │   │   ├── UnifiedSetup.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── UserManagement/
│   │   │   │   │   ├── UserList.jsx
│   │   │   │   │   ├── RoleAssignment.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── BudgetManagement/
│   │   │   │   │   ├── BudgetBuilder.jsx
│   │   │   │   │   └── index.ts
│   │   │   │   ├── AdminPanel.jsx
│   │   │   │   └── index.ts
│   │   │   ├── Auth/
│   │   │   │   ├── LoginForm.jsx
│   │   │   │   ├── ProtectedRoute.jsx
│   │   │   │   └── index.ts
│   │   │   ├── Common/
│   │   │   │   ├── Header.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   ├── ErrorBoundary.jsx
│   │   │   │   ├── LoadingSpinner.jsx
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── AdminPage.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── NotFoundPage.jsx
│   │   │   └── index.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useFetch.ts
│   │   │   ├── useRBAC.ts
│   │   │   ├── useCostData.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts                # Axios client
│   │   │   ├── auth.ts               # Authentication
│   │   │   ├── cost.ts               # Cost API calls
│   │   │   ├── aws.ts                # AWS API calls
│   │   │   ├── azure.ts              # Azure API calls
│   │   │   ├── gcp.ts                # GCP API calls
│   │   │   ├── user.ts               # User management
│   │   │   └── index.ts
│   │   │
│   │   ├── types/
│   │   │   ├── api.ts
│   │   │   ├── domain.ts
│   │   │   ├── models.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── styles/
│   │   │   ├── globals.css
│   │   │   ├── variables.css
│   │   │   ├── dashboard.css
│   │   │   ├── admin.css
│   │   │   └── components.css
│   │   │
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── vite-env.d.ts
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   └── logo.png
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── services/
│   │   ├── integration/
│   │   ├── fixtures/
│   │   └── setup.ts
│   │
│   ├── Dockerfile
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── .env.example
│   ├── .eslintrc.js
│   ├── jest.config.js
│   └── README.md
│
├── infrastructure/                   # Infrastructure as Code
│   ├── docker-compose.yml            # Local development
│   ├── docker-compose.prod.yml       # Production
│   │
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── redis-deployment.yaml
│   │   ├── ingress.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   ├── RBAC/
│   │   │   ├── role.yaml
│   │   │   ├── rolebinding.yaml
│   │   │   └── serviceaccount.yaml
│   │   └── README.md
│   │
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── aws/
│   │   ├── azure/
│   │   ├── gcp/
│   │   └── README.md
│   │
│   ├── scripts/
│   │   ├── setup.sh                  # One-time setup
│   │   ├── deploy.sh                 # Deploy to production
│   │   ├── migrate.sh                # Run migrations
│   │   ├── backup.sh                 # Database backup
│   │   └── README.md
│   │
│   └── README.md
│
├── docs/                             # Documentation
│   ├── architecture/
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── DATABASE_SCHEMA.md
│   │   ├── DATA_FLOW.md
│   │   ├── SAAS_PRODUCT_ARCHITECTURE.md
│   │   ├── IMPLEMENTATION_STATUS_MATRIX.md
│   │   ├── RBAC_AND_AI_DASHBOARD_SPECS.md
│   │   └── README.md
│   │
│   ├── api/
│   │   ├── COST_API.md
│   │   ├── AWS_API.md
│   │   ├── AZURE_API.md
│   │   ├── GCP_API.md
│   │   ├── USER_API.md
│   │   └── README.md
│   │
│   ├── setup/
│   │   ├── AWS_SETUP.md
│   │   ├── AZURE_SETUP.md
│   │   ├── GCP_SETUP.md
│   │   ├── LOCAL_DEVELOPMENT.md
│   │   └── README.md
│   │
│   ├── guides/
│   │   ├── DEVELOPMENT.md
│   │   ├── DEPLOYMENT.md
│   │   ├── RBAC_GUIDE.md
│   │   ├── CONTRIBUTING.md
│   │   └── TESTING.md
│   │
│   ├── operations/
│   │   ├── MONITORING.md
│   │   ├── TROUBLESHOOTING.md
│   │   ├── SCALING.md
│   │   └── BACKUP_RECOVERY.md
│   │
│   └── README.md
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # Run tests on PR
│   │   ├── deploy-dev.yml            # Deploy to dev on merge
│   │   ├── deploy-prod.yml           # Deploy to prod (manual)
│   │   ├── code-quality.yml          # Linting, coverage
│   │   └── security-scan.yml         # Security scanning
│   │
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── tech_debt.md
│   │
│   └── pull_request_template.md
│
├── config/
│   ├── schedules.yaml                # Job schedules
│   ├── logging.yaml                  # Logging configuration
│   ├── feature-flags.yaml
│   └── README.md
│
├── scripts/
│   ├── setup.sh                      # Initial setup
│   ├── dev.sh                        # Start dev environment
│   ├── test.sh                       # Run tests
│   ├── lint.sh                       # Run linters
│   └── README.md
│
├── .gitignore
├── .dockerignore
├── .env.example
├── Makefile                          # Common tasks
├── README.md                         # Project overview
├── LICENSE
├── CHANGELOG.md
└── VERSION
```

---

## Migration Steps

### Phase 1: Create New Structure (2-3 hours)

1. Create new directories at repo root level
2. Move files to appropriate locations
3. Update Python imports
4. Update JavaScript imports
5. Update configuration files

### Phase 2: Update Code References (2-3 hours)

1. Fix all import statements
2. Update router registration
3. Update job registration
4. Update environment variables

### Phase 3: Update Configuration (1-2 hours)

1. Update docker-compose.yml
2. Update GitHub Actions
3. Update deployment configs
4. Create environment templates

### Phase 4: Testing & Validation (2-3 hours)

1. Unit tests
2. Integration tests
3. End-to-end verification
4. Git cleanup

---

## Key Improvements

**Separation of Concerns:**
- ✅ Backend isolated from frontend
- ✅ API routes organized by resource
- ✅ Jobs organized by cloud provider
- ✅ Business logic in services
- ✅ Cloud connectors centralized

**Scalability:**
- ✅ Easy to add new cloud providers
- ✅ Easy to add new features
- ✅ Clear dependency structure
- ✅ Testable architecture

**Maintainability:**
- ✅ Self-documenting structure
- ✅ Easy to onboard new developers
- ✅ Clear ownership boundaries
- ✅ Infrastructure-as-code organized

**DevOps:**
- ✅ Docker-ready structure
- ✅ Kubernetes manifests included
- ✅ CI/CD templates included
- ✅ Deployment scripts included

---

## Files to Move/Reorganize

### Backend Files
```
OLD → NEW

backend/app/models.py → backend/app/models.py
backend/app/main.py → backend/app/main.py
backend/app/database.py → backend/app/database.py
backend/app/settings.py → backend/app/settings.py
backend/app/schemas.py → backend/app/schemas.py

backend/app/routes_cost.py → backend/app/api/v1/cost/routes.py
backend/app/connectors.py → backend/app/connectors/base.py

backend/app/aws_cur_ingest.py → backend/app/jobs/aws/cur_ingest.py
backend/app/aws_focus_transform.py → backend/app/jobs/shared/focus_transform.py
backend/app/azure_jobs.py → backend/app/jobs/azure/cost_api_ingest.py
backend/app/gcp_jobs.py → backend/app/jobs/gcp/bigquery_ingest.py
backend/app/jobs.py → backend/app/jobs/scheduler.py

backend/app/seed_cost_mappings.py → backend/app/seed/mappings/

backend/app/recommendations.py → backend/app/services/recommendation_service.py
backend/app/evaluator.py → backend/app/services/recommendation_service.py
backend/app/connectors.py → backend/app/services/cloud_service.py
```

### Frontend Files
```
OLD → NEW

frontend/src/pages/CostDashboards.jsx → frontend/src/components/Dashboard/*/
frontend/src/pages/AdminCostSetup.jsx → frontend/src/components/Admin/CostSetup/
```

---

## Import Update Examples

**Before:**
```python
# In backend/app/main.py
from app.jobs import run_cost_ingest
from app.routes_cost import router as cost_router
from app.routes_aws import router as aws_router
from app.models import CostDetail
```

**After:**
```python
# In backend/app/main.py
from app.jobs.scheduler import start_scheduler
from app.api.v1 import get_api_router
from app.models import CostDetail
```

**Before:**
```jsx
// In frontend/src/pages/CostDashboards.jsx
import axios from 'axios';
```

**After:**
```jsx
// In frontend/src/components/Dashboard/Executive/ExecutiveSummary.jsx
import axios from 'axios';
import { useCostData } from '../../../hooks/useCostData';
import { CostSummary } from '../../../types/domain';
```

---

## Commands to Execute

```bash
# Will be provided in next message
```
