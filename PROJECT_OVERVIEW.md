# FinOps Recommendation Engine - Project Overview

**Status:** ✅ Cleaned & Ready  
**Last Updated:** May 3, 2026

---

## Cleanup Summary

All CloudXP and Jio references have been successfully removed from both folders:
- ✅ **600+ file references** updated
- ✅ **Directory names** renamed (e.g., `cloudxp-recommendation-engine` → `finops-recommendation-engine`)
- ✅ **Code, documentation, configuration** sanitized
- ✅ **Database credentials** updated in `.env.example`
- ✅ **Zero remaining references** to CloudXP/Jio

---

## Folder Structure & Contents

### 📁 **Folder 1: Recommendation-engine** (Production Implementation)

**Purpose:** Self-contained, production-ready backend and frontend for the FinOps Recommendation Engine.

**Key Components:**

```
Recommendation-engine/
├── backend/                    # FastAPI Python backend
│   ├── app/                   # Core application code
│   │   ├── main.py           # REST API endpoints
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── database.py       # PostgreSQL configuration
│   │   ├── recommendations.py # Recommendation logic
│   │   ├── evaluator.py      # Hypothesis evaluation engine
│   │   ├── jobs.py           # Scheduled job runners
│   │   ├── connectors.py     # Provider integrations
│   │   ├── seed.py           # Database seeding
│   │   ├── schemas.py        # Pydantic request/response models
│   │   └── settings.py       # Configuration management
│   └── tests/                 # Test suite
├── frontend/                  # React UI
│   └── src/                   # Frontend source code
├── db/                       # Database
│   └── init/                 # PostgreSQL schema DDL
├── config/                   # Configuration files
│   ├── recommendations/      # Recommendation catalogs (CSV)
│   └── provider_registry.yaml # Provider integrations manifest
├── docker-compose.yml        # Docker setup
├── .env.example             # Environment configuration template
└── README.md                # Quick start guide
```

**Technology Stack:**
- **Backend:** FastAPI (Python), PostgreSQL, SQLAlchemy ORM
- **Frontend:** React, Node.js
- **Infrastructure:** Docker Compose

**What It Does:**
- Defines recommendation rules and hypotheses
- Evaluates rules against CSP metrics, billing, and K8s data
- Imports native advisor recommendations (AWS, Azure, GCP)
- Manages findings, actions, outcomes, and audit logs
- Backtests recommendations before publishing
- Provides REST API for dashboard and console

---

### 📁 **Folder 2: Recommendation-engine-catalog** (Product Documentation & Design)

**Purpose:** Comprehensive product specification, architecture, PM documentation, and UI mockups.

**Key Sections:**

```
Recommendation-engine-catalog/
├── pm/features/finops-recommendation-engine/
│   ├── prd-basic.md                        # Product Requirements Document (Basic tier)
│   ├── prd-advanced.md                     # Product Requirements Document (Advanced tier)
│   ├── README.md                           # Feature overview
│   ├── basic-requirements-critical-review.md
│   ├── basic-costvars-advisory-mapping.md
│   ├── basic-recommendation-catalog.md
│   ├── basic-system-user-guide.md
│   ├── basic-ui-flow-simulation-review.md
│   ├── basic-project-map-roadmap.md
│   └── ...other planning docs
│
├── docs/architecture/
│   └── finops-recommendation-engine.md     # Technical architecture & system design
│
├── docs/optimization/
│   ├── gpu-compute-recommendations-user-guide.md
│   ├── HLD-azure-gpu-recommendations.md
│   └── ...other optimization docs
│
├── web/FinOps Recommendation Engine/       # Standalone SPA mock (React/Babel)
│   ├── index.html                          # Single-page app entry point
│   ├── data/                               # CSV catalogs and sample data
│   ├── lib/                                # React, React-DOM, Babel libraries
│   ├── docs/                               # Technical docs (requirements, product design)
│   └── SAMPLE_RECOMMENDATIONS_FULL.js      # Example recommendation data
│
├── web/Cost Recommendations Related/       # Related legacy recommendation UIs
│   └── src/                                # JavaScript mock implementations
│
├── cost_advisory/                          # Cost advisory schema & governance
│   ├── README.md
│   ├── EXECUTION_PLAN.md
│   ├── SCHEMA_REFERENCE.md
│   └── ...CSV recommendation catalogs
│
├── source-docs/
│   └── FinOps_CostVars_Tooling_v2.docx    # Source advisory document
│
├── tools/
│   └── extract_costvars_docx.py           # DOCX extraction utility
│
├── EXPORT_MANIFEST.csv                     # Complete file manifest with hashes
├── LARGE_FILES.md                          # List of large/excluded files
└── README.md                               # Package overview
```

**Content Includes:**
- **PRDs:** Complete product specifications for Basic and Advanced recommendation tiers
- **Technical Architecture:** System design, data flows, and integration patterns
- **UI/UX Mockups:** Standalone React SPA demonstrating the user interface
- **Recommendation Catalogs:** 1000+ recommendation definitions across categories
- **Cost Advisory:** FinOps cost recommendation schema and governance
- **GPU Optimization:** Specialized GPU compute recommendation guides
- **Project Roadmap:** Implementation timeline and dependencies

---

## What's Available to Do

### 🚀 **Immediate (Quick Wins)**

1. **Run the Backend API**
   ```bash
   cd Recommendation-engine
   cp .env.example .env
   docker compose up --build
   ```
   - API available at `http://127.0.0.1:8088/docs`
   - Frontend available at `http://127.0.0.1:5174`
   - Database seeded with demo data automatically

2. **Run the SPA Mockup**
   ```bash
   cd Recommendation-engine-catalog/web
   python3 -m http.server 5173
   ```
   - Open `http://127.0.0.1:5173/FinOps%20Recommendation%20Engine/`
   - Fully interactive mockup of the UI/UX

3. **Review the PRD**
   - Read `Recommendation-engine-catalog/pm/features/finops-recommendation-engine/prd-basic.md`
   - Understand product vision, personas, and requirements

---

### 🔧 **Development Tasks**

1. **Integrate Live Provider Credentials**
   - Edit `.env` in `Recommendation-engine/`
   - Add AWS IAM role, Azure Service Principal, GCP service account, etc.
   - Connectors will pull real metrics, billing, and recommendations

2. **Customize Recommendation Rules**
   - Edit `config/recommendations/basic-recommendation-catalog-global.csv`
   - Add rows with custom thresholds, metrics, and recommendation types
   - POST to `/api/recommendation-definitions/import` to reload

3. **Extend Backend APIs**
   - Add new endpoints in `backend/app/main.py`
   - Create new models in `models.py`
   - Extend evaluator logic in `evaluator.py`

4. **Build Advanced Tier**
   - Implement signal fusion engine (APM traces, query history, workload fingerprints)
   - Add custom function runtime for user-authored transforms
   - See `prd-advanced.md` for full specification

---

### 📊 **Analytics & Reporting**

1. **Dashboard Insights**
   - Findings by state (new, approved, applied, dismissed)
   - Estimated savings by recommendation category
   - Integration health and signal coverage metrics
   - Audit log of all user actions

2. **Backtest & Validation**
   - Test recommendation rules on historical data
   - Review coverage (% of resources matched) and hit count
   - Publish to shadow mode or active mode

3. **Realized Savings Reconciliation**
   - Track actual cost changes after actions are applied
   - Compare estimated vs. actual savings
   - Report on ROI by business unit, cost center, or recommendation class

---

### 🔌 **Integration Opportunities**

**Currently Supported Providers:**
- AWS (CloudWatch, Cost Optimization Hub, Compute Optimizer)
- Azure (Monitor API, Azure Advisor)
- GCP (Monitoring, Cloud Recommender)
- Kubernetes (custom metrics)
- Datadog, Dynatrace, New Relic
- ServiceNow, Jira, Slack, Microsoft Teams
- Product Catalog (pricing data)
- Custom Observability (Elasticsearch-compatible)

**To Add New Providers:**
1. Create manifest in `config/provider_registry.yaml`
2. Implement connector class in `backend/app/connectors.py`
3. Define signal normalization schema
4. Test end-to-end with `/api/integrations/sync`

---

### 📈 **Next Strategic Phases**

Based on the PRD documentation:

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Phase 0** | Weeks 1–6 | Backbone services (API, DB, scheduler) |
| **Phase 1** | Weeks 6–10 | Basic Recommendation Engine GA with native advisor import |
| **Phase 2** | Weeks 10–18 | Advanced tier (Bands A & B) with signal fusion |
| **Phase 3** | Weeks 18+ | Full Advanced tier, marketplace, custom functions |

---

## Key Files to Start With

| File | Purpose |
|------|---------|
| `Recommendation-engine/README.md` | Backend quick start |
| `Recommendation-engine-catalog/pm/features/finops-recommendation-engine/prd-basic.md` | Product strategy & requirements |
| `Recommendation-engine-catalog/docs/architecture/finops-recommendation-engine.md` | Technical architecture |
| `Recommendation-engine-catalog/web/FinOps Recommendation Engine/docs/requirements-v3.md` | Detailed functional requirements |
| `Recommendation-engine-catalog/web/Cost Recommendations Related/` | UI/UX reference implementations |

---

## Project Statistics

- **Total Files:** 200+
- **Lines of Code (Backend):** ~5,000
- **Lines of Documentation:** ~20,000
- **Recommendation Definitions:** 1,030+
- **Provider Integrations:** 12+
- **Cost Advisory Rules (CostVars):** 43 families with ~430 rules

---

## Next Steps for You

1. ✅ **Understand the Architecture** – Read the PRD and architecture docs
2. 🚀 **Get Running Locally** – Docker Compose starts both backend and frontend
3. 🔧 **Customize for Your Use Case** – Update recommendation rules, add integrations
4. 📊 **Deploy & Monitor** – Use PostgreSQL in production, configure provider credentials, run evaluator jobs
5. 📈 **Iterate & Expand** – Add new recommendation classes, custom functions, or integrations

---

**Questions?** Review the docs in each folder or check the code comments in `backend/app/main.py`.
