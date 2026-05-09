# Import Migration Guide

**Purpose:** Helps developers update import statements after project restructuring

---

## Python Imports

### Backend App Imports

#### Database & Models
```python
# OLD
from models import CostDetail, User, Config

# NEW
from app.models import CostDetail, User, Config
```

#### API Routes
```python
# OLD (in main.py)
from routes_cost import router as cost_router
from routes_aws import router as aws_router

# NEW (in main.py)
from app.api.v1 import get_api_router
api_router = get_api_router()
app.include_router(api_router)
```

#### Jobs & Scheduler
```python
# OLD
from jobs import start_scheduler
from aws_cur_ingest import run_cost_ingest
from azure_jobs import run_azure_ingest

# NEW
from app.jobs.scheduler import start_scheduler
from app.jobs.aws.cur_ingest import run_cost_ingest
from app.jobs.azure.cost_api_ingest import run_azure_ingest
```

#### Services
```python
# OLD
from recommendations import generate_recommendations
from evaluator import run_evaluator

# NEW
from app.services.recommendation_service import generate_recommendations
from app.services.evaluator import run_evaluator
```

#### Connectors
```python
# OLD
from connectors import AWSConnector, AzureConnector

# NEW
from app.connectors.aws.s3_connector import AWSConnector
from app.connectors.azure.cost_api_connector import AzureConnector
```

#### Seed Data
```python
# OLD
from seed import seed_all_mappings
from seed_cost_mappings import seed_aws_product_categories

# NEW
from app.seed.seed_data import seed_all_mappings
from app.seed.mappings.aws_mappings import seed_aws_product_categories
from app.seed.mappings.azure_mappings import seed_azure_product_categories
from app.seed.mappings.gcp_mappings import seed_gcp_product_categories
```

#### Settings & Configuration
```python
# OLD
from settings import Settings
import os

# NEW
from app.settings import Settings

settings = Settings()  # Dependency injection preferred
```

---

## JavaScript/TypeScript Imports

### Component Imports

#### From absolute paths
```javascript
// OLD
import CostDashboards from '../pages/CostDashboards'
import AdminSetup from '../pages/AdminCostSetup'

// NEW
import { ExecutiveSummary } from '@/components/Dashboard/Executive/ExecutiveSummary'
import { FinancePortal } from '@/components/Dashboard/Finance/FinancePortal'
import { AdminPanel } from '@/components/Admin/AdminPanel'
```

#### Service imports
```javascript
// OLD
import axios from 'axios'

// NEW
import { apiClient } from '@/services/api'
import { costService } from '@/services/cost'
import { authService } from '@/services/auth'
```

#### Hook imports
```javascript
// OLD
// hooks were inline

// NEW
import { useAuth } from '@/hooks/useAuth'
import { useCostData } from '@/hooks/useCostData'
import { useRBAC } from '@/hooks/useRBAC'
```

#### Type imports
```javascript
// OLD
// types were inline

// NEW
import type { CostSummary, CostDetail } from '@/types/domain'
import type { ApiResponse } from '@/types/api'
```

---

## API Endpoint Paths

### Old Paths
```
GET  /api/cost/summary
GET  /api/cost/daily
GET  /api/cost/by-service
GET  /api/ingest-config
POST /api/ingest-config
PATCH /api/ingest-config/{id}
GET  /api/status
GET  /api/ai-services
```

### New Paths (After Restructuring)
```
# Same endpoints, but using versioned API
GET  /api/v1/cost/summary
GET  /api/v1/cost/daily
GET  /api/v1/cost/by-service
GET  /api/v1/aws/ingest-config
POST /api/v1/aws/ingest-config
GET  /api/v1/azure/ingest-config
POST /api/v1/azure/ingest-config
GET  /api/v1/gcp/ingest-config
POST /api/v1/gcp/ingest-config
GET  /api/v1/health/status
GET  /api/v1/users/profile
```

---

## Frontend Service Updates

### API Client

```typescript
// OLD: frontend/src/api.ts
import axios from 'axios'

const client = axios.create({
  baseURL: '/api'
})

// NEW: frontend/src/services/api.ts
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1'
})

// Add request interceptor for auth
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### Cost Service

```typescript
// NEW: frontend/src/services/cost.ts
import { apiClient } from './api'

export const costService = {
  getSummary: (tenantId: string, days: number) =>
    apiClient.get(`/cost/summary`, { params: { tenant_id: tenantId, days } }),
  
  getDaily: (tenantId: string) =>
    apiClient.get(`/cost/daily`, { params: { tenant_id: tenantId } }),
  
  getByService: (tenantId: string, service: string) =>
    apiClient.get(`/cost/by-service`, { 
      params: { tenant_id: tenantId, service } 
    }),
}
```

### AWS Service

```typescript
// NEW: frontend/src/services/aws.ts
import { apiClient } from './api'

export const awsService = {
  getConfigs: (tenantId: string) =>
    apiClient.get(`/aws/ingest-config`, { params: { tenant_id: tenantId } }),
  
  createConfig: (config: AwsConfigInput) =>
    apiClient.post(`/aws/ingest-config`, config),
  
  testConnection: (configId: string) =>
    apiClient.post(`/aws/test-connection`, { config_id: configId }),
}
```

### Azure Service

```typescript
// NEW: frontend/src/services/azure.ts
import { apiClient } from './api'

export const azureService = {
  getConfigs: (tenantId: string) =>
    apiClient.get(`/azure/ingest-config`, { params: { tenant_id: tenantId } }),
  
  createConfig: (config: AzureConfigInput) =>
    apiClient.post(`/azure/ingest-config`, config),
  
  testConnection: (configId: string) =>
    apiClient.post(`/azure/test-connection`, { config_id: configId }),
}
```

### GCP Service

```typescript
// NEW: frontend/src/services/gcp.ts
import { apiClient } from './api'

export const gcpService = {
  getConfigs: (tenantId: string) =>
    apiClient.get(`/gcp/ingest-config`, { params: { tenant_id: tenantId } }),
  
  createConfig: (config: GcpConfigInput) =>
    apiClient.post(`/gcp/ingest-config`, config),
  
  testConnection: (configId: string) =>
    apiClient.post(`/gcp/test-connection`, { config_id: configId }),
}
```

---

## Component Updates

### Dashboard Component

```typescript
// OLD: frontend/src/pages/CostDashboards.jsx
import React, { useState, useEffect } from 'react'
import axios from 'axios'

export function FinancePortal() {
  const [summary, setSummary] = useState(null)
  
  useEffect(() => {
    const fetchData = async () => {
      const summaryRes = await axios.get('/api/cost/summary', {
        params: { tenant_id: 'tenant-demo', days: 90 }
      })
      setSummary(summaryRes.data)
    }
    fetchData()
  }, [])
  // ...
}

// NEW: frontend/src/components/Dashboard/Finance/FinancePortal.jsx
import React, { useState, useEffect } from 'react'
import { useCostData } from '@/hooks/useCostData'
import { costService } from '@/services/cost'

export function FinancePortal() {
  const { data: summary, loading } = useCostData(
    () => costService.getSummary('tenant-demo', 90),
    []
  )
  
  // ...
}
```

### Admin Component

```typescript
// OLD: frontend/src/pages/AdminCostSetup.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'

export function AdminCostSetup() {
  const [configs, setConfigs] = useState([])
  
  const fetchConfigs = async () => {
    const res = await axios.get('/api/cost/ingest-config')
    setConfigs(res.data.configs || [])
  }
  // ...
}

// NEW: frontend/src/components/Admin/UnifiedSetup.jsx
import { useState, useEffect } from 'react'
import { awsService, azureService, gcpService } from '@/services'
import { AwsSetup } from './CostSetup/AwsSetup'
import { AzureSetup } from './CostSetup/AzureSetup'
import { GcpSetup } from './CostSetup/GcpSetup'

export function UnifiedSetup() {
  const [activeTab, setActiveTab] = useState('aws')
  
  return (
    <div>
      <tabs>
        <tab name="aws"><AwsSetup /></tab>
        <tab name="azure"><AzureSetup /></tab>
        <tab name="gcp"><GcpSetup /></tab>
      </tabs>
    </div>
  )
}
```

---

## Environment Variables

### Backend (.env)

```bash
# OLD location: backend/.env
# NEW location: backend/.env (same, but with updated paths)

DATABASE_URL=postgresql://user:pass@localhost/finops
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ENVIRONMENT=development
LOG_LEVEL=info

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# Azure Configuration
AZURE_SUBSCRIPTION_ID=xxx
AZURE_TENANT_ID=xxx
AZURE_CLIENT_ID=xxx
AZURE_CLIENT_SECRET=xxx

# GCP Configuration
GCP_PROJECT_ID=xxx
GCP_CREDENTIALS_PATH=/path/to/credentials.json
```

### Frontend (.env)

```bash
# OLD location: frontend/.env
# NEW location: frontend/.env (same structure)

VITE_API_URL=http://localhost:8000
VITE_API_PREFIX=/api/v1
VITE_AUTH_PROVIDER=okta
VITE_AUTH_DOMAIN=your-domain.okta.com
```

---

## Configuration Files

### docker-compose.yml

```yaml
# OLD: Recommendation-engine/docker-compose.yml
# NEW: infrastructure/docker-compose.yml

version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/finops
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=finops
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Import Checklist

- [ ] Update all Python imports in `backend/app/main.py`
- [ ] Update all API route registrations in `backend/app/main.py`
- [ ] Update all job registrations in `backend/app/jobs/scheduler.py`
- [ ] Update all imports in job files
- [ ] Update all imports in service files
- [ ] Update all imports in connector files
- [ ] Update all imports in test files
- [ ] Update all JavaScript imports in `frontend/src/services/api.ts`
- [ ] Update all component imports in dashboard components
- [ ] Update all component imports in admin components
- [ ] Update API endpoint paths in frontend services
- [ ] Update environment variable references
- [ ] Update docker-compose.yml paths
- [ ] Run backend tests: `python -m pytest backend/tests`
- [ ] Run frontend tests: `npm test`
- [ ] Run dev server: `docker-compose up`
- [ ] Test all API endpoints manually
- [ ] Commit changes with: `git commit -m "refactor: update imports after restructuring"`
