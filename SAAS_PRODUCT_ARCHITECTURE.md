# FinOps SaaS Product - Complete Architecture & Capabilities

**Status:** Specification & Gap Analysis  
**Date:** May 9, 2026  
**Scope:** Multi-cloud cost management platform with enterprise-grade RBAC

---

## Executive Summary

The FinOps SaaS platform is a multi-cloud cost aggregation, normalization, and optimization system supporting AWS, Azure, and GCP. This document provides a complete specification of:

1. **Current UI State**: What has been built (credential management for AWS, 4 persona dashboards)
2. **UI Gaps**: What needs to be added (multi-cloud credential UI, CSP-specific dashboards, FOCUS normalized view, AI cost dashboard)
3. **RBAC Architecture**: Current state and recommended enterprise implementation
4. **Complete Product Capabilities**: Feature list for a production SaaS offering

---

## Part 1: UI Implementation Status

### Currently Built ✅

#### 1. Admin Cost Setup UI (`AdminCostSetup.jsx`)
- **Purpose**: AWS CUR ingestion configuration management
- **Features**:
  - Create, edit, delete AWS CUR ingest configurations
  - S3 bucket, prefix, IAM role ARN, external ID input
  - Configuration validation (ARN format, required fields)
  - Job status monitoring (cost_ingest, focus_transform)
  - Setup instructions (4-step wizard)
  - Test connection button
  - Configuration listing with status badges

- **Credentials Collected**:
  - S3 bucket name (S3 access only)
  - AWS IAM Role ARN (cross-account)
  - External ID (security)
  - Tenant ID (multi-tenant isolation)

- **Architecture**:
  - Tenant-scoped endpoints: `/api/cost/ingest-config`
  - POST, GET, PATCH, DELETE operations
  - Job status polling: `/api/cost/status`

#### 2. Cost Dashboards (`CostDashboards.jsx`)
- **Purpose**: Four persona-based cost analysis views
- **Features**:
  - **Executive Summary**: C-level overview with annual spend, quarterly forecasts, strategic insights
  - **Finance Portal**: CFO view with 90-day trends, cost drivers, account breakdown
  - **FinOps Analytics**: Detailed service analysis, AI service breakdown, optimization recommendations
  - **Team Cost Dashboard**: Cost allocation by team/project, budget tracking, resource listing

- **Data Visualizations**:
  - Line charts (cost trends)
  - Bar charts (category, service breakdown)
  - Pie charts (cost distribution)
  - Data tables (detailed costs, AI services)
  - KPI cards (summary metrics)

- **Key Metrics**:
  - Total cost (absolute, averages)
  - Monthly burn rate
  - Cost by category/service/account/team
  - AI service costs with unit pricing
  - Budget status and allocation
  - Optimization opportunities

- **Data Sources**:
  - `/api/cost/summary`: Summary metrics
  - `/api/cost/daily`: Daily cost trends
  - `/api/ai-services`: AI service breakdown
  - Calls use `tenant_id` parameter for multi-tenant isolation

---

### UI Gaps ❌ (Needs Implementation)

#### 1. Multi-Cloud Credential Management UI

**Current State**: AWS-only credential UI

**Required Additions**:

**A. Azure Credential Form**
```
Form Fields:
- Azure Subscription ID (text input)
- Azure Tenant ID (text input)
- Service Principal Client ID (text input)
- Service Principal Client Secret (password input, encrypted)
- Billing Scope (select: /subscriptions/{id} or /providers/Microsoft.Billing/...)
- Export Frequency (select: Daily/Monthly)
- Data Source (select: standard/detailed)
- Enabled toggle

Endpoints:
- POST /api/azure/ingest-config
- GET /api/azure/ingest-config
- PATCH /api/azure/ingest-config/{id}
- POST /api/azure/test-connection?config_id={id}

Components:
- AzureCredentialForm (form component)
- AzureConfigCard (display credential config)
- AzureJobStatusMonitor (monitor azure_ingest, azure_focus_transform jobs)
```

**B. GCP Credential Form**
```
Form Fields:
- GCP Project ID (text input)
- Service Account Email (text input)
- Service Account Key JSON (large textarea, encrypted)
- Billing Account ID (text input)
- BigQuery Dataset (text input, default "billing_export")
- BigQuery Table (text input, default "gcp_billing_export_v1")
- Export Frequency (select: Daily/Monthly)
- Data Source (select: standard/detailed)
- Enabled toggle

Endpoints:
- POST /api/gcp/ingest-config
- GET /api/gcp/ingest-config
- PATCH /api/gcp/ingest-config/{id}
- POST /api/gcp/test-connection?config_id={id}

Components:
- GcpCredentialForm (form component)
- GcpConfigCard (display credential config)
- GcpJobStatusMonitor (monitor gcp_ingest, gcp_focus_transform jobs)
```

**C. Unified Multi-Cloud Admin UI**
```
Components Needed:
- CloudProviderTabs: Navigation between AWS/Azure/GCP configuration sections
- CredentialManagementHub: Unified view of all credentials across providers
- CloudProviderStatus: Dashboard showing:
  - Last sync time per provider
  - Data freshness (hours since last update)
  - Records ingested (last 24h, last 7d)
  - Cost coverage (% of spend ingested)
- MigrationTools: Bulk operations across providers

Layout:
┌─────────────────────────────────────────┐
│ Cost Management Admin Panel             │
├─────────────────────────────────────────┤
│ [AWS] [Azure] [GCP] [All Providers]    │
├─────────────────────────────────────────┤
│ AWS Configurations                      │
│  - Existing form and config cards       │
│                                         │
│ [+ New AWS Configuration]               │
├─────────────────────────────────────────┤
│ Azure Configurations                    │
│  - Azure form and config cards          │
│ [+ New Azure Configuration]             │
├─────────────────────────────────────────┤
│ GCP Configurations                      │
│  - GCP form and config cards            │
│ [+ New GCP Configuration]               │
├─────────────────────────────────────────┤
│ Provider Status Overview                │
│  AWS:   ✓ Active (2 configs) 15min sync │
│  Azure: ✓ Active (1 config) 45min sync  │
│  GCP:   ✓ Active (1 config) 20min sync  │
│                                         │
│ Job Status & History (unified)          │
│  cost_ingest [AWS, Azure, GCP]          │
│  focus_transform [unified]              │
│  azure_ingest [running, 2500 records]   │
│  gcp_ingest [success, 5100 records]     │
└─────────────────────────────────────────┘
```

---

#### 2. Cloud Provider-Specific Dashboards

**Current State**: None (all dashboards show aggregated data)

**Required CSP-Specific Views**:

**A. AWS Cost Dashboard** (`AWSCostDashboard.jsx`)
```
Components:
1. Account Breakdown
   - Table: Account ID, Organization Path, Total Cost, MoM Change
   - Filter by linked account, organization unit
   
2. Service Analysis
   - Top services by cost (EC2, RDS, S3, etc.)
   - Usage metrics per service
   - Reserved Instance utilization
   
3. AWS-Specific Metrics
   - On-Demand vs Reserved vs Spot breakdown
   - Savings Plans coverage
   - Unused resources (unattached EBS, idle RDS)
   - Data transfer costs (CloudFront, inter-region)
   
4. Regional Breakdown
   - Cost by region
   - Data transfer matrix
   
5. Savings Opportunities (AWS-specific)
   - Reserved Instance recommendations
   - Savings Plans potential
   - Unused resource cleanup
   
6. RI/SP Utilization
   - Current coverage %
   - Cost savings achieved vs potential
```

**B. Azure Cost Dashboard** (`AzureCostDashboard.jsx`)
```
Components:
1. Subscription Breakdown
   - Table: Subscription ID, Name, Total Cost, Budget Status
   - Filter by subscription, resource group
   
2. Service Analysis
   - Top services by cost (VM, App Service, Storage, SQL Database)
   - Usage metrics per service
   - Reservation utilization
   
3. Azure-Specific Metrics
   - Reserved Instances vs Pay-as-You-Go
   - Azure Hybrid Benefit utilization
   - Cost by resource group
   - Departmental allocation (billing tags)
   
4. Regional Breakdown
   - Cost by region
   - Bandwidth costs
   
5. Savings Opportunities (Azure-specific)
   - Reserved Instance recommendations
   - Azure Hybrid Benefit potential
   - Commitment discounts coverage
   
6. Commitment Tracker
   - Current commitments and utilization
   - Upcoming commitment expirations
```

**C. GCP Cost Dashboard** (`GcpCostDashboard.jsx`)
```
Components:
1. Project Breakdown
   - Table: Project ID, Name, Total Cost, Billing Account
   - Filter by project, billing account
   
2. Service Analysis
   - Top services by cost (Compute Engine, Cloud Storage, BigQuery, etc.)
   - Usage metrics per service
   - Commitment discount utilization
   
3. GCP-Specific Metrics
   - Committed Use Discount (CUD) coverage
   - Preemptible vs on-demand instances
   - Flex Slots usage
   - Labels breakdown (cost center, environment, team)
   
4. Regional Breakdown
   - Cost by region/zone
   - Inter-region egress costs
   
5. Savings Opportunities (GCP-specific)
   - CUD recommendations
   - Preemptible instance potential
   - Flex Slots optimization
   - Storage class optimization
   
6. CUD Tracker
   - Current commitments
   - Utilization % and unit prices
   - Upcoming commitment expirations
```

---

#### 3. FOCUS-Normalized Multi-Cloud Dashboard

**Current State**: None (dashboards show raw/aggregated data, not explicitly FOCUS-normalized)

**Required Component** (`FocusNormalizedDashboard.jsx`)

```
Purpose: Unified view across all clouds using FOCUS-standard fields

Components:

1. FOCUS Field Selector
   - Dropdown: Choose primary grouping
     - invoice_issuer (AWS, Azure, GCP)
     - service_name (unified across clouds)
     - service_category (Compute, Storage, Database, Networking, AI/ML, Analytics)
     - resource_location (region, normalized)
     - billing_period
     - cost_type (usage, tax, adjustment, credit)

2. Cost Breakdown (FOCUS-Standard)
   ┌──────────────────────────────────────────┐
   │ By Service Category (FOCUS Standard)     │
   ├──────────────────────────────────────────┤
   │ Category       | AWS      | Azure | GCP  │
   │ Compute        | $45,200  | $12K  | $8K  │
   │ Storage        | $12,100  | $3K   | $2K  │
   │ Database       | $28,400  | $7K   | $5K  │
   │ Networking     | $8,900   | $1K   | $800 │
   │ AI/ML          | $15,600  | $4K   | $3K  │
   │ Analytics      | $6,200   | $1K   | $2K  │
   │ ─────────────────────────────────────────│
   │ TOTAL          | $116,400 | $28K  | $21K │
   └──────────────────────────────────────────┘

3. Usage vs Cost Analysis
   - Show billed_cost vs usage_quantity
   - Normalized unit costs across providers ($/GB, $/vCPU, $/request)
   - Identify pricing differences for equivalent services

4. Cost Allocation (FOCUS Tags)
   - Unified tag view across clouds
   - Group by cost_center, environment, team, application
   - Cross-cloud tag consistency checker

5. Billing Period Analysis
   - FOCUS billing_period_start/end normalization
   - Reconcile different billing cycles (AWS daily vs Azure monthly vs GCP daily)
   - Period-over-period comparison

6. Cost Type Breakdown (FOCUS)
   - Usage costs vs Adjustments vs Credits vs Taxes
   - By service and category
   
7. Time Dimension
   - FOCUS-normalized daily costs across all providers
   - Consistent calendar (all providers normalized to UTC daily buckets)
   - Trend analysis with consistent date handling

8. Raw FOCUS Records
   - Drill-down table showing actual FOCUS records
   - Columns: invoice_issuer, service_name, billing_period_start, 
             usage_quantity, billed_cost, service_category, tags
```

---

#### 4. AI Services Cost Dashboard

**Current State**: FinOpsAnalytics component has basic AI services table

**Required Enhanced Dashboard** (`AICostDashboard.jsx`)

```
Purpose: Detailed AI/LLM cost analysis and optimization

Components:

1. AI Service Inventory
   ┌──────────────────────────────────────────────────┐
   │ All AI Services in Use                           │
   ├──────────────────────────────────────────────────┤
   │ Service           | Provider | Status | Cost 30d │
   │ Claude 3 (Opus)   | AWS/API  | Active | $12,450  │
   │ GPT-4             | Azure    | Active | $8,230   │
   │ Vertex AI         | GCP      | Active | $5,120   │
   │ Bedrock (Titan)   | AWS      | Inactive| $230    │
   │ OpenAI Embeddings | Azure    | Active | $340     │
   │ Vision API        | GCP      | Active | $520     │
   │ Speech-to-Text    | GCP      | Active | $80      │
   └──────────────────────────────────────────────────┘

2. Model-Level Cost Breakdown
   Service: Claude 3 (Opus) - $12,450 (30d)
   ├─ Input tokens (2.5B)      $7,500   (60%)
   ├─ Output tokens (400M)     $4,800   (38%)
   └─ Batch processing         $150     (1%)
   
   By Application:
   ├─ Data Analysis             $5,200
   ├─ Customer Support          $3,400
   ├─ Code Generation           $2,800
   └─ Other                     $1,050

3. Token Economics
   - Input token cost per M
   - Output token cost per M
   - Cost per input vs output ratio
   - Trend over time (token price decreases, volume increase)

4. Usage Metrics
   - Requests per day (30-day trend)
   - Tokens per request (input, output)
   - Cache hit rates (if available)
   - Processing time vs cost correlation

5. AI Service Comparison
   ┌───────────────────────────────┐
   │ Price/Performance Comparison  │
   ├───────────────────────────────┤
   │ Service      | Cost/1M Input  │
   │ Claude 3 Opus|     $3.00      │
   │ GPT-4        |     $3.00      │
   │ Vertex PaLM  |     $0.50      │
   │ Azure OpenAI |     $2.00      │
   └───────────────────────────────┘

6. Cost Optimization Recommendations
   - Use Claude 3 Haiku/Sonnet for lower-cost applications
   - Enable caching for frequently-accessed contexts
   - Batch processing for non-real-time workloads
   - Reserved capacity / commitment discounts
   - Monitoring for runaway costs/token abuse

7. Anomaly Detection
   - Spike detection: Unusual token usage increases
   - Service abuse: Potential unintended API calls
   - Cost per request trending

8. Budget Tracking (AI-Specific)
   - Budgets by service (Claude, GPT-4, etc.)
   - Budgets by application/project
   - Current vs forecasted
   - Alert thresholds

9. Integration Points
   - Link to code repositories (GitHub integration)
   - Link to logs (which applications are making calls)
   - Request tracing (origin, latency, success rate)

10. Model Versioning & Cost Impact
    - When did Claude 3 Opus pricing change?
    - How many tokens used at old vs new price?
    - Migration impact if changing models
```

---

## Part 2: RBAC (Role-Based Access Control) Architecture

### Current State

**Currently**: No RBAC implemented. All users have access to all data for tenant_id='tenant-demo'.

### Recommended RBAC Architecture

#### 1. Authentication Layer

```
Authentication Flow:
┌──────────────┐
│ User Login   │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ OAuth 2.0 Provider   │ (Okta, Auth0, Cognito, etc.)
│ - Tenant claim       │
│ - User roles         │
│ - Department claim   │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ JWT Token            │ (with tenant_id, roles, permissions)
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ Application          │ (validates token, enforces RBAC)
└──────────────────────┘
```

#### 2. Role Hierarchy

```
GLOBAL ROLES (apply to entire organization):

1. FinOps Admin
   - Full access to all cloud credentials
   - Can create/edit/delete configurations
   - Can manage users and roles
   - Can access all dashboards
   - Can access AI service inventory
   - Can set budgets and alerts
   Permissions:
   - AWS: read AWS/Azure/GCP configs, test connections, delete configs
   - Azure: read Azure/AWS/GCP configs, test connections, delete configs
   - GCP: read GCP/AWS/Azure configs, test connections, delete configs
   - Dashboard: all views (Finance, FinOps, Team, Executive, CSP-specific, FOCUS, AI)
   - Admin: user management, role assignment, settings

2. FinOps Engineer
   - View all cost data
   - Configure new ingestion sources
   - Cannot delete configurations
   - Can create reports and exports
   - Can manage optimization recommendations
   - Cannot manage users
   Permissions:
   - AWS/Azure/GCP: read configs, test connections (no delete)
   - Dashboard: all cost views
   - Reports: create, edit, export
   - Recommendations: view, create, manage status

3. Finance Manager
   - View Finance Portal dashboard
   - View Executive Summary
   - Can set budgets and cost thresholds
   - View cost allocations by team/project
   - Generate financial reports
   - Cannot modify cloud credentials
   - Cannot access detailed service-level costs
   Permissions:
   - Dashboard: Finance Portal, Executive Summary, Team Dashboard
   - Budget: create, edit, manage alerts
   - Reports: generate, export
   - Configs: read-only (no create/edit/delete)

4. Team Lead / Manager
   - View costs for their team/project only
   - View Team Cost Dashboard (filtered)
   - Budget tracking for their allocation
   - Cannot see other teams' costs
   - Cannot modify any configurations
   Permissions:
   - Dashboard: Team Dashboard (scoped to team_id)
   - Cost data: scoped to cost_center or project_id
   - Budget: read their team's budget
   - Reports: export team costs

5. Finance Analyst
   - View all cost dashboards (read-only)
   - View detailed service-level breakdowns
   - Run custom cost queries
   - Generate reports
   - View recommendations
   - Cannot modify configurations or users
   Permissions:
   - Dashboard: all cost views (read-only)
   - Reports: create custom queries, export
   - Recommendations: view

6. Viewer (Limited)
   - View Executive Summary only
   - Read-only access to high-level metrics
   - No dashboard access except Executive
   Permissions:
   - Dashboard: Executive Summary (read-only)
   - No configs, no reports, no detailed data
```

#### 3. Scoped Access (Row-Level Security)

```
SCOPE: Cost data visibility based on organizational structure

1. By Tenant (Multi-Tenant)
   tenant_id: org-acme-corp
   
   All data filtered by:
   WHERE tenant_id = 'org-acme-corp'
   
   User cannot see other tenant data

2. By Department/Cost Center (within tenant)
   User: finance-manager@acme-corp
   Assigned to: Finance Department
   
   Dashboard filters:
   WHERE tenant_id = 'org-acme-corp' AND cost_center IN ('Finance', 'CFO')
   
   Cannot see Engineering, Marketing, Sales costs

3. By Project (within tenant)
   User: team-lead@acme-corp
   Assigned to: Project 'payment-platform'
   
   Cost data filters:
   WHERE tenant_id = 'org-acme-corp' AND project_id = 'payment-platform'
   
   Cannot see costs from other projects

4. By Cloud Account (within tenant)
   User: aws-engineer@acme-corp
   Assigned to: AWS Account '123456789012'
   
   Cost data filters:
   WHERE tenant_id = 'org-acme-corp' AND account_id = '123456789012'
   
   Cannot see costs from Azure subscription or GCP project

5. By Cloud Provider (within tenant)
   User: gcp-specialist@acme-corp
   Assigned to: GCP provider
   
   Cost data filters:
   WHERE tenant_id = 'org-acme-corp' AND invoice_issuer = 'gcp'
   
   Cannot see AWS or Azure costs
```

#### 4. Database Schema for RBAC

```sql
-- User table
CREATE TABLE app_user (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    oauth_sub VARCHAR(255) UNIQUE,  -- Auth provider subject
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant(id)
);

-- Role definition
CREATE TABLE app_role (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,  -- FinOps Admin, Finance Manager, etc.
    description TEXT,
    global_role BOOLEAN DEFAULT false,  -- false = scoped role
    created_at TIMESTAMP,
    UNIQUE(tenant_id, name)
);

-- Permission definition
CREATE TABLE permission (
    id UUID PRIMARY KEY,
    code VARCHAR(255) UNIQUE NOT NULL,  -- "cost:read", "config:write", "user:manage"
    description TEXT,
    resource_type VARCHAR(50),  -- "cost", "config", "user", "dashboard"
    action VARCHAR(50),  -- "read", "write", "delete", "manage"
    created_at TIMESTAMP
);

-- Role-Permission mapping
CREATE TABLE role_permission (
    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES app_role(id),
    FOREIGN KEY (permission_id) REFERENCES permission(id)
);

-- User-Role assignment
CREATE TABLE user_role (
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    assigned_by UUID,
    assigned_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional temporary assignment
    PRIMARY KEY (user_id, role_id, tenant_id),
    FOREIGN KEY (user_id) REFERENCES app_user(id),
    FOREIGN KEY (role_id) REFERENCES app_role(id)
);

-- Row-level scope assignment
CREATE TABLE user_scope (
    user_id UUID NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    scope_type VARCHAR(50) NOT NULL,  -- "department", "project", "cloud_account", "cloud_provider"
    scope_value VARCHAR(255) NOT NULL,  -- actual value (org-unit-123, project-abc, etc.)
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, scope_type, scope_value),
    FOREIGN KEY (user_id) REFERENCES app_user(id)
);

-- Audit log
CREATE TABLE rbac_audit_log (
    id UUID PRIMARY KEY,
    actor_id UUID,
    action VARCHAR(100),  -- "user_created", "role_assigned", "permission_granted"
    target_user_id UUID,
    tenant_id VARCHAR(255),
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMP,
    ip_address VARCHAR(45),
    FOREIGN KEY (actor_id) REFERENCES app_user(id),
    FOREIGN KEY (target_user_id) REFERENCES app_user(id)
);
```

#### 5. API-Level RBAC Enforcement

```python
# FastAPI middleware for RBAC

from fastapi import Request, HTTPException
from functools import wraps

def require_permission(permission_code: str):
    """Decorator to enforce permission checks on endpoints"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Extract JWT token
            token = extract_jwt_token(request)
            user = decode_jwt(token)  # Get user_id, tenant_id, roles
            
            # Check if user has permission
            has_perm = check_permission(
                user_id=user['id'],
                tenant_id=user['tenant_id'],
                permission_code=permission_code
            )
            
            if not has_perm:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission_code}"
                )
            
            # Add user context to request
            request.state.user_id = user['id']
            request.state.tenant_id = user['tenant_id']
            request.state.scopes = get_user_scopes(user['id'])
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def apply_row_level_security(query, user_id: str, tenant_id: str):
    """Apply row-level filters based on user scopes"""
    scopes = get_user_scopes(user_id)
    
    # Always filter by tenant
    query = query.filter(CostDetail.tenant_id == tenant_id)
    
    # Apply scope filters
    for scope in scopes:
        if scope['type'] == 'department':
            query = query.filter(CostDetail.cost_center == scope['value'])
        elif scope['type'] == 'project':
            query = query.filter(CostDetail.project_id == scope['value'])
        elif scope['type'] == 'cloud_account':
            query = query.filter(CostDetail.account_id == scope['value'])
        elif scope['type'] == 'cloud_provider':
            query = query.filter(CostDetail.invoice_issuer == scope['value'])
    
    return query

# Example endpoint
@app.get("/api/cost/daily")
@require_permission("cost:read")
async def get_daily_costs(request: Request, tenant_id: str):
    user_id = request.state.user_id
    
    # Build base query
    query = db.query(CostDetail)
    
    # Apply RBAC
    query = apply_row_level_security(query, user_id, tenant_id)
    
    # Execute and return
    costs = query.all()
    return {"data": costs}
```

#### 6. Frontend RBAC Implementation

```jsx
// React component for RBAC-aware UI

import { useAuth } from './hooks/useAuth';

export function CostDashboardRouter() {
  const { user, hasPermission, getUserScopes } = useAuth();
  
  return (
    <div className="dashboard-router">
      <div className="tab-navigation">
        {/* Show tabs based on permissions */}
        {hasPermission('dashboard:executive') && (
          <button onClick={() => setActiveTab('executive')}>
            Executive Summary
          </button>
        )}
        
        {hasPermission('dashboard:finance') && (
          <button onClick={() => setActiveTab('finance')}>
            Finance Portal
          </button>
        )}
        
        {hasPermission('dashboard:finops') && (
          <button onClick={() => setActiveTab('finops')}>
            FinOps Analytics
          </button>
        )}
        
        {hasPermission('dashboard:team') && (
          <button onClick={() => setActiveTab('team')}>
            Team Dashboard
          </button>
        )}
        
        {hasPermission('dashboard:csp') && (
          <button onClick={() => setActiveTab('csp')}>
            Cloud Provider View
          </button>
        )}
      </div>
      
      <div className="tab-content">
        {activeTab === 'executive' && <ExecutiveSummary />}
        {activeTab === 'finance' && <FinancePortal />}
        {activeTab === 'finops' && <FinOpsAnalytics />}
        {activeTab === 'team' && <TeamCostDashboard user={user} />}
        {activeTab === 'csp' && <CSPDashboard user={user} />}
      </div>
    </div>
  );
}

// Scoped component example
export function TeamCostDashboard({ user }) {
  const scopes = getUserScopes();
  const [teamCosts, setTeamCosts] = useState([]);
  
  useEffect(() => {
    // Fetch costs scoped to user's assigned teams
    const filters = {
      tenant_id: user.tenant_id,
      ...getFilterFromScopes(scopes)
    };
    
    fetchTeamCosts(filters).then(setTeamCosts);
  }, [user, scopes]);
  
  return (
    <div className="team-dashboard">
      <h2>Team Costs{scopes.length > 0 ? ` - ${scopes[0].value}` : ''}</h2>
      {/* Render team-specific costs */}
    </div>
  );
}

// Admin panel for user management
export function UserManagementPanel() {
  const { user, hasPermission } = useAuth();
  
  if (!hasPermission('user:manage')) {
    return <div>Access Denied</div>;
  }
  
  return (
    <div className="user-management">
      <h2>User Management</h2>
      
      {/* User list, role assignment, scope assignment */}
      <UserList />
      <RoleAssignmentForm />
      <ScopeAssignmentForm />
    </div>
  );
}
```

---

## Part 3: Complete SaaS Product Capabilities

### Feature Matrix

#### A. Core Cost Aggregation
- [x] AWS CUR ingestion
- [x] Azure Cost Management API
- [x] GCP BigQuery export
- [ ] Multi-cloud roll-up (single config for multiple CSPs)
- [ ] Real-time cost updates (vs. current 5-min polling)
- [ ] Cost forecast modeling
- [ ] Cost anomaly detection
- [ ] Cost attribution and chargeback

#### B. Cost Normalization & Analytics
- [x] FOCUS schema transformation
- [x] Service category mapping
- [x] AI service classification
- [ ] Custom cost allocation rules
- [ ] Hierarchical cost allocation (department → team → project)
- [ ] Cost driver analysis
- [ ] Trend analysis with seasonal adjustments
- [ ] Variance analysis (actual vs. budget)

#### C. Cloud Provider-Specific Features
- [x] AWS CUR parsing
- [x] Azure Cost API integration
- [x] GCP BigQuery integration
- [ ] AWS Compute Optimizer integration
- [ ] Azure Advisor integration
- [ ] GCP Recommender integration
- [ ] Reserved Instance/Commitment tracking (all clouds)
- [ ] Spot/Preemptible instance optimization
- [ ] Data transfer cost optimization

#### D. Dashboards & Reporting
- [x] Executive Summary
- [x] Finance Portal
- [x] FinOps Analytics
- [x] Team Cost Dashboard
- [ ] CSP-specific dashboards (AWS, Azure, GCP)
- [ ] FOCUS-normalized multi-cloud view
- [ ] AI cost dashboard
- [ ] Custom dashboard builder
- [ ] Scheduled report generation
- [ ] Report distribution (email, Slack, etc.)

#### E. Cost Optimization
- [ ] Right-sizing recommendations
- [ ] Unused resource detection
- [ ] Commitment discount optimization
- [ ] Spot/Preemptible/Low-Priority instance recommendations
- [ ] Data transfer optimization
- [ ] Storage tier optimization
- [ ] Reserved capacity planning
- [ ] Cost-benefit analysis for optimizations
- [ ] Automated remediation (turn off resources, change settings)

#### F. Budgeting & Governance
- [x] Budget tracking (basic, in Team Dashboard)
- [ ] Hierarchical budgets (org → dept → team → project)
- [ ] Budget vs actual tracking
- [ ] Forecasting and alerting
- [ ] Budget enforcement (cost controls)
- [ ] Approval workflows for over-budget situations
- [ ] Policy enforcement (auto-stop resources, tags, etc.)
- [ ] Cost allocation rulesets
- [ ] Chargeback automation

#### G. AI/LLM Cost Management
- [ ] AI service inventory
- [ ] Model-level cost tracking
- [ ] Token usage analytics
- [ ] Cost per token optimization
- [ ] AI service cost forecasting
- [ ] Budget enforcement for AI spend
- [ ] Anomaly detection (runaway costs)
- [ ] AI service comparison and recommendations
- [ ] Integration with LLM observability platforms

#### H. Marketplace & FinOps Recommendations
- [ ] CSP-native recommendations import
- [ ] Third-party recommendation engine integration
- [ ] Custom recommendation builder
- [ ] Recommendation tracking and status
- [ ] Savings attribution
- [ ] Recommendation ROI calculation
- [ ] Backtest hypotheses against historical data
- [ ] A/B testing framework for optimizations

#### I. APIs & Integrations
- [x] REST API for cost data
- [ ] GraphQL API
- [ ] Webhook support (cost alerts, recommendations)
- [ ] AWS/Azure/GCP service integrations
- [ ] Slack integration (alerts, reports)
- [ ] PagerDuty/OpsGenie integration
- [ ] Datadog/New Relic integration
- [ ] ServiceNow integration
- [ ] Jira integration (for tracking optimization tasks)
- [ ] Custom webhook for third-party systems

#### J. Security & Compliance
- [x] Multi-tenant isolation
- [x] Tenant-scoped data filtering
- [ ] RBAC with role hierarchy
- [ ] Row-level security (scoped access)
- [ ] Audit logging (all actions)
- [ ] SAML/OAuth 2.0 SSO
- [ ] MFA support
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Secrets management (credential encryption)
- [ ] SOC 2 Type II compliance
- [ ] HIPAA compliance
- [ ] GDPR compliance (data retention, deletion)

#### K. Administration & Operations
- [x] Cloud credential management (AWS)
- [ ] Multi-cloud credential management (Azure, GCP)
- [ ] Credential rotation
- [ ] Unified credential hub
- [ ] Job scheduling and monitoring
- [ ] Data pipeline monitoring
- [ ] Database migration tools
- [ ] Backup and restore
- [ ] Disaster recovery procedures
- [ ] Performance tuning
- [ ] Capacity planning

#### L. User Management
- [ ] User provisioning/deprovisioning
- [ ] Role assignment
- [ ] Scope assignment (department, project, account, provider)
- [ ] Team management
- [ ] Organization structure modeling
- [ ] User activity tracking
- [ ] Delegation (one user impersonating another for support)
- [ ] Single Sign-On (SSO)
- [ ] Multi-factor authentication (MFA)

#### M. Data & Analytics
- [ ] Custom cost query builder (SQL-like interface)
- [ ] Data export (CSV, Parquet, Excel)
- [ ] BI tool integration (Tableau, Looker, Power BI)
- [ ] Time series analysis
- [ ] Statistical anomaly detection
- [ ] Machine learning for forecasting
- [ ] Cohort analysis (comparing similar resources)
- [ ] Data lineage (show data origin and transformations)

#### N. Mobile & Accessibility
- [ ] Mobile app (iOS/Android)
- [ ] Mobile dashboard (responsive web)
- [ ] Mobile alerts and notifications
- [ ] WCAG 2.1 accessibility compliance
- [ ] Dark mode
- [ ] Localization (i18n)

---

### Implementation Roadmap

#### Phase 10: Multi-Cloud UI Expansion (4 weeks)
- [ ] Implement Azure credential management UI
- [ ] Implement GCP credential management UI
- [ ] Build unified multi-cloud admin panel
- [ ] AWS, Azure, GCP dashboard tabs

#### Phase 11: Advanced Dashboards (3 weeks)
- [ ] Cloud provider-specific dashboards (AWS, Azure, GCP)
- [ ] FOCUS-normalized multi-cloud dashboard
- [ ] AI cost dashboard with token tracking
- [ ] Custom dashboard builder (basic)

#### Phase 12: RBAC System (3 weeks)
- [ ] User and role management UI
- [ ] Permission framework
- [ ] Row-level security implementation
- [ ] Audit logging

#### Phase 13: Optimization & Recommendations (4 weeks)
- [ ] CSP-native recommendations API integration
- [ ] Recommendation tracking and status
- [ ] Cost impact calculation
- [ ] Backtest framework

#### Phase 14: Budgeting & Governance (3 weeks)
- [ ] Hierarchical budget builder
- [ ] Budget vs actual tracking
- [ ] Alerts and notifications
- [ ] Approval workflows

#### Phase 15: Enterprise Features (4 weeks)
- [ ] SSO/SAML integration
- [ ] Advanced audit logging
- [ ] Compliance reporting (SOC 2, HIPAA)
- [ ] Data retention policies

---

## Conclusion

The FinOps SaaS platform has a strong foundation with core cost ingestion, FOCUS normalization, and persona-based dashboards. The next phase focuses on:

1. **Multi-Cloud Credential Management**: Extend UI for Azure and GCP
2. **CSP-Specific Views**: Leverage cloud-native strengths
3. **FOCUS Normalization**: Unified multi-cloud analytics
4. **AI Cost Dashboard**: Monitor expensive new workloads
5. **RBAC System**: Enterprise-grade access control
6. **Advanced Features**: Optimization, budgeting, governance

Success metrics:
- **User Adoption**: % of organization using platform
- **Cost Visibility**: % of cloud spend tracked and visible
- **Optimization Impact**: $ saved through recommendations
- **ROI**: Savings vs. platform cost
