# Project Restructuring - Execution Guide

**Total Estimated Time:** 4-6 hours  
**Risk Level:** Medium (backed up, reversible)  
**Date:** May 9, 2026

---

## Phase 0: Preparation (30 minutes)

### Step 1: Review Documents
- [ ] Read `PROJECT_RESTRUCTURING_PLAN.md`
- [ ] Understand new directory structure
- [ ] Review import changes in `IMPORT_MIGRATION_GUIDE.md`

### Step 2: Create Git Branch
```bash
cd /path/to/finops-saas
git checkout -b refactor/project-structure
git pull origin main
```

### Step 3: Commit Current State
```bash
git add .
git commit -m "checkpoint: save current state before restructuring"
```

---

## Phase 1: Execute Directory Restructuring (1 hour)

### Step 1: Make the Script Executable
```bash
chmod +x restructure.sh
```

### Step 2: Run the Restructuring Script
```bash
./restructure.sh
```

**Expected Output:**
```
==================================
FinOps SaaS Project Restructuring
==================================
✅ Backup created at: .backup-1715000000
✅ Directory structure created
✅ Backend code moved
✅ Frontend code moved
✅ Configuration files moved
✅ Python package initializers created
✅ Documentation files created
✅ .gitignore files created

✅ Restructuring Complete!
```

### Step 3: Verify Directory Structure
```bash
# Check that all directories were created
ls -la backend/
ls -la frontend/
ls -la infrastructure/
ls -la docs/
```

### Step 4: Check Git Status
```bash
git status
```

**Expected:** All new files should be untracked (red), old Recommendation-engine structure still exists

---

## Phase 2: Update Python Imports (1.5 hours)

### Step 1: Update Main Application File

**File:** `backend/app/main.py`

```python
# BEFORE
from app.jobs import run_cost_ingest, run_aws_focus_transform
from app.routes_cost import router as cost_router
from app.routes_aws import router as aws_router
from app.routes_azure import router as azure_router
from app.routes_gcp import router as gcp_router

# AFTER
from app.jobs.scheduler import start_scheduler
from app.api.v1 import get_api_router

# In app initialization:
# OLD
app.include_router(cost_router)
app.include_router(aws_router)
# ...
scheduler = start_scheduler()  # from app.jobs

# NEW
api_router = get_api_router()
app.include_router(api_router)
scheduler = start_scheduler()
```

### Step 2: Create Route Initialization File

**File:** `backend/app/api/v1/__init__.py`

```python
"""API v1 routes"""
from fastapi import APIRouter

def get_api_router():
    """Register all API routers and return combined router"""
    router = APIRouter(prefix="/api/v1")
    
    try:
        from .cost.routes import router as cost_router
        router.include_router(cost_router, tags=["cost"])
    except ImportError:
        print("⚠️  Cost router not found")
    
    try:
        from .aws.routes import router as aws_router
        router.include_router(aws_router, prefix="/aws", tags=["aws"])
    except ImportError:
        print("⚠️  AWS router not found")
    
    try:
        from .azure.routes import router as azure_router
        router.include_router(azure_router, prefix="/azure", tags=["azure"])
    except ImportError:
        print("⚠️  Azure router not found")
    
    try:
        from .gcp.routes import router as gcp_router
        router.include_router(gcp_router, prefix="/gcp", tags=["gcp"])
    except ImportError:
        print("⚠️  GCP router not found")
    
    try:
        from .health.routes import router as health_router
        router.include_router(health_router, tags=["health"])
    except ImportError:
        print("⚠️  Health router not found")
    
    return router
```

### Step 3: Update Job Files

**File:** `backend/app/jobs/scheduler.py`

```python
# Update imports at top
from app.jobs.aws.cur_ingest import run_cost_ingest  # renamed from aws_cur_ingest
from app.jobs.shared.focus_transform import run_focus_transform
from app.jobs.azure.cost_api_ingest import run_azure_ingest
from app.jobs.gcp.bigquery_ingest import run_gcp_ingest
from app.jobs.shared.recommendation_engine import run_evaluator

# Rest of file remains the same
```

### Step 4: Update Service Imports

Update imports in all service files:

```python
# In backend/app/services/recommendation_service.py
from app.models import CostDetail, FocusCost, Recommendation
from app.database import SessionLocal
from app.settings import settings

# In backend/app/services/evaluator.py
from app.models import CostDetail, Signal, Hypothesis
from app.database import SessionLocal
```

### Step 5: Run Python Tests

```bash
cd backend
python -m pytest tests/ -v
```

**Expected:** All tests should pass (or show same errors as before)

---

## Phase 3: Update JavaScript Imports (1 hour)

### Step 1: Update Service Files

**File:** `frontend/src/services/api.ts`

```typescript
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_PREFIX = '/api/v1'

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token to requests
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default apiClient
```

### Step 2: Create Specialized Services

Create the following files in `frontend/src/services/`:

**File:** `frontend/src/services/cost.ts`

```typescript
import { apiClient } from './api'

export const costService = {
  getSummary: (tenantId: string, days: number = 90) =>
    apiClient.get('/cost/summary', {
      params: { tenant_id: tenantId, days }
    }),
  
  getDaily: (tenantId: string) =>
    apiClient.get('/cost/daily', {
      params: { tenant_id: tenantId }
    }),
  
  getByService: (tenantId: string, service?: string) =>
    apiClient.get('/cost/by-service', {
      params: { tenant_id: tenantId, service }
    }),
  
  getStatus: (limit: number = 10) =>
    apiClient.get('/cost/status', { params: { limit } })
}
```

**File:** `frontend/src/services/aws.ts`

```typescript
import { apiClient } from './api'

export const awsService = {
  getConfigs: (tenantId: string) =>
    apiClient.get('/aws/ingest-config', {
      params: { tenant_id: tenantId }
    }),
  
  createConfig: (data: any) =>
    apiClient.post('/aws/ingest-config', data),
  
  updateConfig: (id: string, data: any) =>
    apiClient.patch(`/aws/ingest-config/${id}`, data),
  
  deleteConfig: (id: string) =>
    apiClient.delete(`/aws/ingest-config/${id}`),
  
  testConnection: (configId: string) =>
    apiClient.post('/aws/test-connection', { config_id: configId })
}
```

**File:** `frontend/src/services/azure.ts`

```typescript
import { apiClient } from './api'

export const azureService = {
  getConfigs: (tenantId: string) =>
    apiClient.get('/azure/ingest-config', {
      params: { tenant_id: tenantId }
    }),
  
  createConfig: (data: any) =>
    apiClient.post('/azure/ingest-config', data),
  
  updateConfig: (id: string, data: any) =>
    apiClient.patch(`/azure/ingest-config/${id}`, data),
  
  deleteConfig: (id: string) =>
    apiClient.delete(`/azure/ingest-config/${id}`),
  
  testConnection: (configId: string) =>
    apiClient.post('/azure/test-connection', { config_id: configId })
}
```

**File:** `frontend/src/services/gcp.ts`

```typescript
import { apiClient } from './api'

export const gcpService = {
  getConfigs: (tenantId: string) =>
    apiClient.get('/gcp/ingest-config', {
      params: { tenant_id: tenantId }
    }),
  
  createConfig: (data: any) =>
    apiClient.post('/gcp/ingest-config', data),
  
  updateConfig: (id: string, data: any) =>
    apiClient.patch(`/gcp/ingest-config/${id}`, data),
  
  deleteConfig: (id: string) =>
    apiClient.delete(`/gcp/ingest-config/${id}`),
  
  testConnection: (configId: string) =>
    apiClient.post('/gcp/test-connection', { config_id: configId })
}
```

**File:** `frontend/src/services/index.ts`

```typescript
export * from './api'
export * from './cost'
export * from './aws'
export * from './azure'
export * from './gcp'
export * from './auth'  // if exists
```

### Step 3: Update Component Imports

**File:** `frontend/src/components/Dashboard/DashboardRouter.jsx`

```jsx
// OLD
import { FinancePortal } from '../pages/CostDashboards'

// NEW
import { FinancePortal } from './Finance/FinancePortal'
import { ExecutiveSummary } from './Executive/ExecutiveSummary'
import { FinOpsAnalytics } from './FinOps/FinOpsAnalytics'
import { TeamCostDashboard } from './Team/TeamDashboard'
```

**File:** `frontend/src/components/Admin/AdminPanel.jsx`

```jsx
// OLD
import AdminCostSetup from '../pages/AdminCostSetup'

// NEW
import { AwsSetup } from './CostSetup/AwsSetup'
import { AzureSetup } from './CostSetup/AzureSetup'
import { GcpSetup } from './CostSetup/GcpSetup'
```

### Step 4: Run Frontend Tests

```bash
cd frontend
npm test
```

**Expected:** Tests should compile with new import paths

---

## Phase 4: Update Configuration (30 minutes)

### Step 1: Update Docker Compose

**File:** `infrastructure/docker-compose.yml`

Update paths to match new structure:

```yaml
services:
  backend:
    build:
      context: ./backend  # was ../backend
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/finops

  frontend:
    build:
      context: ./frontend  # was ../frontend
```

### Step 2: Update Environment Files

Create `backend/.env.example`:

```bash
DATABASE_URL=postgresql://user:password@localhost/finops
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ENVIRONMENT=development
LOG_LEVEL=info
```

Create `frontend/.env.example`:

```bash
VITE_API_URL=http://localhost:8000
VITE_API_PREFIX=/api/v1
VITE_ENVIRONMENT=development
```

---

## Phase 5: Verification (1 hour)

### Step 1: Start Development Environment

```bash
cd infrastructure
docker-compose up -d
```

### Step 2: Run Backend Tests

```bash
cd backend
python -m pytest tests/ -v --cov=app
```

**Expected Output:**
```
====== test session starts ======
...
====== X passed in X.XXs ======
```

### Step 3: Start Frontend Dev Server

```bash
cd frontend
npm install  # if dependencies changed
npm run dev
```

**Expected:** Frontend loads at `http://localhost:3000`

### Step 4: Test API Endpoints

```bash
# Test backend is running
curl http://localhost:8000/api/v1/health/status

# Expected response:
# {"status": "ok"}
```

### Step 5: Test API Calls in Frontend

Open browser console at `http://localhost:3000` and test:

```javascript
// In browser console
fetch('http://localhost:8000/api/v1/cost/summary?tenant_id=tenant-demo&days=30')
  .then(r => r.json())
  .then(d => console.log(d))
```

### Step 6: Verify All Dashboards Load

- [ ] Navigate to Executive Summary
- [ ] Navigate to Finance Portal
- [ ] Navigate to FinOps Analytics
- [ ] Navigate to Team Dashboard
- [ ] Navigate to Admin Panel

---

## Phase 6: Git & Cleanup (30 minutes)

### Step 1: Remove Duplicate Code

Once verified everything works:

```bash
# Remove old structure
rm -rf Recommendation-engine

# Or if using git-rm for clean history
git rm -r Recommendation-engine
```

### Step 2: Stage All Changes

```bash
git add -A
git status
```

**Expected:** Should see renamed files, new directory structure, deletions

### Step 3: Commit Changes

```bash
git commit -m "refactor: reorganize project structure into enterprise standard

Major changes:
- Moved backend code from Recommendation-engine/backend to root backend/
- Moved frontend code from Recommendation-engine/frontend to root frontend/
- Organized API routes by resource (v1 versioning)
- Organized jobs by cloud provider (AWS, Azure, GCP)
- Centralized services, connectors, and seeding
- Added proper infrastructure-as-code directory
- Updated all Python and JavaScript imports
- Updated Docker configuration
- Added comprehensive documentation

Directory structure now follows industry standards:
- backend/app/api/v1/ - API routes by resource
- backend/app/jobs/ - Background jobs by cloud provider
- backend/app/services/ - Business logic
- backend/app/connectors/ - Cloud SDK integrations
- frontend/src/components/ - Components organized by feature
- frontend/src/services/ - API client services
- infrastructure/ - Docker and Kubernetes configs
- docs/ - Complete documentation
"
```

### Step 4: Push to Branch

```bash
git push origin refactor/project-structure
```

### Step 5: Create Pull Request

On GitHub:
1. Create PR from `refactor/project-structure` to `main`
2. Add description with before/after structure
3. Request code review
4. Merge after approval

---

## Rollback Plan

If something goes wrong:

```bash
# Option 1: Restore from backup directory
cp -r .backup-{timestamp}/* .

# Option 2: Revert git changes
git reset --hard HEAD~1

# Option 3: Switch to original branch
git checkout main
```

---

## Checklist

### Pre-Restructuring
- [ ] Read all documentation
- [ ] Create backup
- [ ] Create git branch
- [ ] Commit current state

### Restructuring Execution
- [ ] Run restructure.sh script
- [ ] Verify directory structure
- [ ] Create route initialization file
- [ ] Update Python imports
- [ ] Update JavaScript imports
- [ ] Update configuration files

### Testing & Verification
- [ ] Run Python tests
- [ ] Run frontend tests
- [ ] Start Docker environment
- [ ] Test API endpoints
- [ ] Load all dashboards
- [ ] Test admin panel

### Final Steps
- [ ] Remove old directory
- [ ] Commit changes
- [ ] Push to branch
- [ ] Create pull request
- [ ] Get code review
- [ ] Merge to main

---

## Timeline Summary

| Phase | Duration | Task |
|-------|----------|------|
| 0 | 30 min | Preparation & review |
| 1 | 1 hour | Directory restructuring |
| 2 | 1.5 hours | Python import updates |
| 3 | 1 hour | JavaScript import updates |
| 4 | 30 min | Configuration updates |
| 5 | 1 hour | Testing & verification |
| 6 | 30 min | Git & cleanup |
| **Total** | **5.5 hours** | **Complete restructuring** |

---

## Support

If you encounter issues:
1. Check `IMPORT_MIGRATION_GUIDE.md` for specific import patterns
2. Review error messages in test output
3. Check backup at `.backup-{timestamp}`
4. Revert with `git reset --hard` if needed
5. Contact team lead for assistance
