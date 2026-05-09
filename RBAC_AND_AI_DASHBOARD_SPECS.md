# RBAC & AI Cost Dashboard - Detailed Specifications

**Date:** May 9, 2026  
**Status:** Specification for Implementation

---

## Part 1: RBAC Implementation Plan

### 1.1 Role Hierarchy (Recommended)

```
┌────────────────────────────────────────────────────────────┐
│                      Role Hierarchy                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│                  FinOps Admin (Super)                     │
│                    ↓        ↓        ↓                     │
│            ┌─────────┴────┬─────────┴──────┐             │
│            ↓              ↓                ↓              │
│      FinOps Eng    Finance Manager    Team Lead          │
│            ↓              ↓                ↓              │
│            └─────────┬────┴────────┬──────┘              │
│                      ↓             ↓                     │
│              Finance Analyst  Viewer (Limited)           │
│                                                            │
└────────────────────────────────────────────────────────────┘

Permissions by Role:

1. FinOps Admin
   ├─ Read/Write/Delete AWS/Azure/GCP configs
   ├─ Test cloud connections
   ├─ Manage users and roles
   ├─ View all dashboards
   ├─ Create/modify budgets
   ├─ Manage alerts and policies
   ├─ Access audit logs
   └─ System settings

2. FinOps Engineer
   ├─ Read AWS/Azure/GCP configs
   ├─ Test cloud connections
   ├─ Create new configs (no delete)
   ├─ View all cost dashboards
   ├─ Create optimization recommendations
   ├─ Track recommendation status
   ├─ Generate custom reports
   └─ No user management

3. Finance Manager
   ├─ Read-only configs (no modify/delete)
   ├─ View Finance Portal dashboard
   ├─ View Executive Summary
   ├─ View Team Cost Dashboard
   ├─ Create and manage budgets
   ├─ Set cost thresholds and alerts
   ├─ Generate financial reports
   ├─ View cost allocations by team
   └─ No optimization or system changes

4. Team Lead
   ├─ View costs for assigned teams ONLY
   ├─ View Team Cost Dashboard (filtered)
   ├─ View team budgets
   ├─ Cannot see other teams' costs
   ├─ Cannot modify any configurations
   └─ No system access

5. Finance Analyst
   ├─ View all dashboards (read-only)
   ├─ View detailed service-level breakdowns
   ├─ Run custom cost queries
   ├─ Generate reports and exports
   ├─ View optimization recommendations
   ├─ Cannot modify configurations
   └─ No user management

6. Viewer (Limited)
   ├─ View Executive Summary only
   ├─ View high-level metrics
   ├─ No detailed dashboard access
   ├─ No data exports
   └─ No system access
```

### 1.2 Scope-Based Access (Row-Level Security)

```
Multi-Level Scoping:

┌─────────────────────────────────────────────┐
│  Tenant (Organization)                      │
│  └─ ACME Corp (org-acme)                   │
│     ├─ Department Scope                     │
│     │  ├─ Finance Department                │
│     │  │  └─ Users: CFO, Finance Manager   │
│     │  ├─ Engineering Department            │
│     │  │  └─ Users: VP Eng, Team Leads     │
│     │  └─ Marketing Department              │
│     │     └─ Users: CMO                    │
│     │                                       │
│     ├─ Project Scope                        │
│     │  ├─ Payment Platform                  │
│     │  │  └─ Users: platform-team          │
│     │  ├─ Analytics Platform                │
│     │  │  └─ Users: data-team              │
│     │  └─ API Gateway                       │
│     │     └─ Users: platform-team          │
│     │                                       │
│     ├─ Cloud Account Scope                  │
│     │  ├─ AWS-Prod (123456789012)          │
│     │  │  └─ Users: aws-engineers          │
│     │  ├─ AWS-Dev (210987654321)           │
│     │  │  └─ Users: aws-engineers, devs    │
│     │  ├─ Azure-Prod (subscription-xyz)    │
│     │  │  └─ Users: azure-engineers        │
│     │  └─ GCP-Prod (acme-prod-project)     │
│     │     └─ Users: gcp-engineers          │
│     │                                       │
│     └─ Cloud Provider Scope                 │
│        ├─ AWS                               │
│        │  └─ Users: aws-specialists        │
│        ├─ Azure                             │
│        │  └─ Users: azure-specialists      │
│        └─ GCP                               │
│           └─ Users: gcp-specialists        │
│                                             │
└─────────────────────────────────────────────┘

Example: User "alice@acme.com"
  - Role: Finance Manager
  - Scopes:
    ├─ Department: Finance Department
    ├─ Project: None (access all)
    ├─ Cloud Account: None (access all)
    └─ Cloud Provider: None (access all)
  
  Cost Data Visibility:
    WHERE tenant_id = 'org-acme'
      AND cost_center = 'Finance'

Example: User "bob@acme.com"
  - Role: Team Lead
  - Scopes:
    ├─ Department: None
    ├─ Project: Payment Platform
    ├─ Cloud Account: AWS-Prod, AWS-Dev
    └─ Cloud Provider: AWS
  
  Cost Data Visibility:
    WHERE tenant_id = 'org-acme'
      AND (project_id = 'payment-platform'
           OR account_id IN ('123456789012', '210987654321'))
      AND invoice_issuer = 'aws'
```

### 1.3 Dashboard Access by Role

```
Dashboard Availability Matrix:

┌──────────────────────┬─────────┬──────┬────────┬───────┬──────┬────────┐
│ Dashboard            │ Admin   │ Eng  │ Finance│ Team  │ Analyst│Viewer  │
├──────────────────────┼─────────┼──────┼────────┼───────┼──────┼────────┤
│ Executive Summary    │    ✓    │  ✓   │   ✓    │   ✓   │  ✓   │   ✓    │
│ Finance Portal       │    ✓    │  ✓   │   ✓    │   ✗   │  ✓   │   ✗    │
│ FinOps Analytics     │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ Team Cost            │    ✓    │  ✓   │   ✓    │   ✓*  │  ✓   │   ✗    │
│ AWS Dashboard        │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ Azure Dashboard      │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ GCP Dashboard        │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ FOCUS Normalized     │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ AI Cost Dashboard    │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ Cost Optimization    │    ✓    │  ✓   │   ✗    │   ✗   │  ✓   │   ✗    │
│ Budget Tracker       │    ✓    │  ✓   │   ✓    │   ✓*  │  ✗   │   ✗    │
│ Admin Panel          │    ✓    │  ✗   │   ✗    │   ✗   │  ✗   │   ✗    │
│ User Management      │    ✓    │  ✗   │   ✗    │   ✗   │  ✗   │   ✗    │
└──────────────────────┴─────────┴──────┴────────┴───────┴──────┴────────┘

* Team Lead sees only their assigned team's data
* All non-admin roles see data scoped to their assigned departments/projects
```

### 1.4 Implementation Steps

```
Week 1-2: Database & Backend
1. Create RBAC tables (user, role, permission, user_role, user_scope)
2. Implement permission checking middleware
3. Add row-level security filtering to all queries
4. Create RBAC audit logging
5. Test permission enforcement

Week 3: API Layer
1. Create user management endpoints (/api/users, /api/roles, /api/permissions)
2. Add RBAC enforcement to all existing endpoints
3. Add scope filtering to all cost queries
4. Create audit log endpoints

Week 4-5: Frontend Layer
1. Build user management UI component
2. Build role assignment component
3. Build scope assignment component
4. Implement role-based UI rendering
5. Add RBAC enforcer hook to all components
6. Test access control

Week 6: Testing & Documentation
1. Unit tests for permission logic
2. Integration tests for RBAC enforcement
3. E2E tests for UI access control
4. Documentation and runbooks
```

---

## Part 2: AI Cost Dashboard Specification

### 2.1 Dashboard Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            AI Cost Dashboard (AICostDashboard.jsx)          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Section 1: AI Service Inventory                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Active AI Services in Use                            │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ Service           Provider  Status  Cost(30d) MoM    │  │
│  │ Claude 3 (Opus)  AWS/API   ✓      $12,450   +8%    │  │
│  │ GPT-4            Azure     ✓      $8,230    -2%    │  │
│  │ Vertex AI        GCP       ✓      $5,120    +15%   │  │
│  │ Bedrock (Titan)  AWS       ✗      $230      -100%  │  │
│  │ Vision API       GCP       ✓      $520      +22%   │  │
│  │ Speech-to-Text   GCP       ✓      $80       +5%    │  │
│  │ Embeddings       Azure     ✓      $340      +10%   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Section 2: Service Detail View (Expandable)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Claude 3 (Opus) - Total: $12,450 (30d)              │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  Cost Breakdown:                                     │  │
│  │  ├─ Input Tokens (2.5B)      $7,500   (60%)         │  │
│  │  ├─ Output Tokens (400M)     $4,800   (38%)         │  │
│  │  ├─ Batch Processing         $150     (1%)          │  │
│  │  └─ Cache Benefits           -$0      (0%)          │  │
│  │                                                       │  │
│  │  Usage Metrics:                                      │  │
│  │  ├─ Requests/day (avg)       450                    │  │
│  │  ├─ Input tokens/request     5,555                  │  │
│  │  ├─ Output tokens/request    888                    │  │
│  │  └─ Cache hit rate           22%                    │  │
│  │                                                       │  │
│  │  Cost/Economics:                                     │  │
│  │  ├─ Cost per 1M input tokens  $3.00                 │  │
│  │  ├─ Cost per 1M output tokens $15.00                │  │
│  │  ├─ Cost per request (avg)    $27.67                │  │
│  │  └─ Trend: ↑ 8% MoM (higher volume)                │  │
│  │                                                       │  │
│  │  By Application:                                     │  │
│  │  ├─ Data Analysis             $5,200   (42%)         │  │
│  │  ├─ Customer Support          $3,400   (27%)         │  │
│  │  ├─ Code Generation           $2,800   (22%)         │  │
│  │  └─ Other                     $1,050   (8%)          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Section 3: Price Comparison                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Multi-Model Cost Comparison (per 1M input tokens)   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │ Claude 3 Opus    ████████ $3.00 (Most expensive)    │  │
│  │ GPT-4            ████████ $3.00                     │  │
│  │ Claude 3 Sonnet  ███      $3.00 (cost-effective)    │  │
│  │ Claude 3 Haiku   █        $0.25 (Recommended)       │  │
│  │ Vertex PaLM      █        $0.50 (Budget option)     │  │
│  │                                                       │  │
│  │ Recommendation: Use Claude 3 Haiku for code reviews │  │
│  │ and simple tasks. Save $4,200/month.                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Section 4: Token Usage Trends (Chart)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 30-Day Token Usage Trend                             │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │ Input Tokens (Billions)                              │  │
│  │    2.8 │     ╱╲    ╱╲                                │  │
│  │    2.5 │    ╱  ╲  ╱  ╲     ╱╲                        │  │
│  │    2.0 │   ╱    ╲╱    ╲   ╱  ╲   ╱╲                  │  │
│  │    1.5 │  ╱            ╲ ╱    ╲ ╱  ╲                │  │
│  │    1.0 │ ╱              ╱      ╱    ╲               │  │
│  │    0.0 └─────────────────────────────────           │  │
│  │        D1   D8   D15   D22   D29                     │  │
│  │                                                       │  │
│  │ Output Tokens (Millions)                              │  │
│  │    500 │                    ╱╲                       │  │
│  │    400 │   ╱╲   ╱╲      ╱╲ ╱  ╲                     │  │
│  │    300 │  ╱  ╲ ╱  ╲    ╱  ╲    ╲ ╱╲                 │  │
│  │    200 │ ╱    ╱    ╲  ╱    ╲    ╱  ╲               │  │
│  │    100 │      ╱      ╲╱      ╲  ╱    ╲              │  │
│  │      0 └─────────────────────────────────           │  │
│  │        D1   D8   D15   D22   D29                     │  │
│  │                                                       │  │
│  │ Insight: Input tokens up 12%, output tokens stable  │  │
│  │ Cost trending up due to higher input volume, not    │  │
│  │ model changes. Optimization potential: use caching  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Section 5: Cost Optimization Recommendations              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Optimization Opportunities & Savings Potential      │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │ 1. 🔴 HIGH: Switch Code Review to Claude 3 Haiku    │  │
│  │    Current: GPT-4 @ $3.00/M input tokens            │  │
│  │    Recommended: Claude 3 Haiku @ $0.25/M            │  │
│  │    Volume: 600M input tokens/month (code reviews)   │  │
│  │    Savings: $1,650/month (92% reduction)            │  │
│  │    Effort: Low (1 day integration)                  │  │
│  │                                                       │  │
│  │ 2. 🟡 MEDIUM: Enable Prompt Caching                 │  │
│  │    Current: No caching, all tokens billed           │  │
│  │    Recommended: Cache common system prompts         │  │
│  │    Potential: 25-40% token reduction               │  │
│  │    Savings: $2,400-3,200/month                     │  │
│  │    Effort: Medium (3 days, integration testing)     │  │
│  │                                                       │  │
│  │ 3. 🟡 MEDIUM: Batch Processing for Non-Real-Time   │  │
│  │    Current: Real-time API calls for all requests   │  │
│  │    Recommended: Use batch API for daily jobs        │  │
│  │    Discount: Batch API is 50% cheaper              │  │
│  │    Volume: 200M input tokens/month (data analysis)  │  │
│  │    Savings: $300/month                              │  │
│  │    Effort: Medium (2 days)                          │  │
│  │                                                       │  │
│  │ 4. 🟢 LOW: Reserved Capacity Planning               │  │
│  │    Current: Pay-as-you-go for all usage            │  │
│  │    Recommended: Reserve 2B tokens/month             │  │
│  │    Discount: 20% off per-token pricing              │  │
│  │    Savings: $1,800/month                            │  │
│  │    Effort: Low (admin setup)                        │  │
│  │                                                       │  │
│  │ TOTAL POTENTIAL SAVINGS: $6,150/month (49%)         │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Section 6: Budget Tracking (AI-Specific)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ AI Budget Status                                     │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │ Service: Claude (all models)                         │  │
│  │ Budget: $15,000/month                                │  │
│  │ YTD Spent: $48,300 (3 months × avg)                 │  │
│  │ Pace: ████████░░ 80% of budget (at 60% of year)    │  │
│  │ Forecast: $64,800 annual (might exceed 20%)         │  │
│  │ Alert: ⚠️ On pace to exceed $60,000 annual budget   │  │
│  │                                                       │  │
│  │ Service: GPT-4                                       │  │
│  │ Budget: $10,000/month                                │  │
│  │ YTD Spent: $24,690                                  │  │
│  │ Pace: ████████░░ 82% of budget                      │  │
│  │ Forecast: $41,150 annual (will exceed)             │  │
│  │ Alert: ⚠️ Requires action or budget increase        │  │
│  │                                                       │  │
│  │ Service: Vertex AI                                   │  │
│  │ Budget: $5,000/month                                 │  │
│  │ YTD Spent: $15,360                                  │  │
│  │ Pace: ████████░░ 102% OVER BUDGET                  │  │
│  │ Forecast: $25,600 annual (EXCEEDED)                │  │
│  │ Alert: 🔴 IMMEDIATE ACTION REQUIRED                │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Section 7: Anomaly Detection & Cost Spikes                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Cost Anomalies Detected (Last 30 Days)              │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │ 🔴 CRITICAL: May 8, 22:00 UTC                       │  │
│  │    Application: data-analysis-pipeline              │  │
│  │    Service: Claude 3 Opus                           │  │
│  │    Spike: 2.1M tokens in 4 hours (3x normal)       │  │
│  │    Cost: $6,300 in 4 hours                          │  │
│  │    Cause: Potential infinite loop or bug            │  │
│  │    Action: SUSPENDED - Requires investigation       │  │
│  │    Status: Stopped at 22:47 UTC (cost: ~$9,500)    │  │
│  │                                                       │  │
│  │ 🟡 WARNING: May 5, 14:00 UTC                        │  │
│  │    Application: customer-support                    │  │
│  │    Service: Claude 3 Sonnet                         │  │
│  │    Spike: 800K tokens in 2 hours (2.5x normal)     │  │
│  │    Cost: $2,400 in 2 hours                          │  │
│  │    Cause: Marketing campaign drove support volume   │  │
│  │    Action: Escalated to team lead                   │  │
│  │    Status: Investigated - legitimate traffic        │  │
│  │                                                       │  │
│  │ 🟢 INFO: May 1-3, baseline increase                 │  │
│  │    All services +15% usage (within normal range)    │  │
│  │    Reason: Customer onboarding week                 │  │
│  │    Status: Monitored - no action needed             │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Model for AI Services

```sql
-- AI Service Cost Tracking

CREATE TABLE ai_service_usage (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,  -- 'Claude 3 Opus', 'GPT-4', 'Vertex AI', etc.
    provider VARCHAR(50) NOT NULL,        -- 'aws', 'azure', 'gcp', 'openai'
    model_name VARCHAR(255),              -- specific model version
    application_name VARCHAR(255),        -- where it's used
    usage_date DATE NOT NULL,
    input_tokens BIGINT,
    output_tokens BIGINT,
    requests_count INT,
    input_cost DECIMAL(20,10),
    output_cost DECIMAL(20,10),
    batch_cost DECIMAL(20,10),
    cache_benefits DECIMAL(20,10),       -- credit from cache hits
    total_cost DECIMAL(20,10),
    cost_per_request DECIMAL(20,10),
    cache_hit_rate DECIMAL(5,2),
    status VARCHAR(50),                   -- 'active', 'inactive', 'suspended'
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    INDEX idx_tenant_date (tenant_id, usage_date),
    INDEX idx_service_date (service_name, usage_date)
);

CREATE TABLE ai_service_budget (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    monthly_budget DECIMAL(20,2) NOT NULL,
    spending_limit VARCHAR(50),           -- 'hard' or 'soft'
    alert_threshold_pct INT DEFAULT 80,   -- alert when 80% of budget
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by UUID,
    FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    UNIQUE(tenant_id, service_name)
);

CREATE TABLE ai_service_anomaly (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    application_name VARCHAR(255),
    detected_at TIMESTAMP,
    anomaly_type VARCHAR(50),             -- 'spike', 'drift', 'pattern_change'
    baseline_tokens BIGINT,
    anomaly_tokens BIGINT,
    baseline_cost DECIMAL(20,2),
    anomaly_cost DECIMAL(20,2),
    severity VARCHAR(20),                 -- 'critical', 'warning', 'info'
    status VARCHAR(50),                   -- 'new', 'acknowledged', 'resolved'
    investigation_notes TEXT,
    action_taken VARCHAR(255),            -- 'suspended', 'monitored', 'none'
    resolved_at TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    INDEX idx_tenant_severity (tenant_id, severity, detected_at)
);

CREATE TABLE ai_model_pricing (
    id UUID PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,        -- 'aws', 'azure', 'gcp', 'openai'
    model_name VARCHAR(255) NOT NULL,     -- 'claude-3-opus', 'gpt-4', etc.
    input_cost_per_1m_tokens DECIMAL(10,6) NOT NULL,
    output_cost_per_1m_tokens DECIMAL(10,6) NOT NULL,
    batch_discount_pct DECIMAL(5,2),      -- 50% for batch APIs
    cache_discount_pct DECIMAL(5,2),      -- 90% for cached tokens
    effective_date DATE,
    end_date DATE,
    UNIQUE(provider, model_name, effective_date)
);

CREATE TABLE ai_optimization_recommendation (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    service_affected VARCHAR(255),
    application_affected VARCHAR(255),
    current_monthly_cost DECIMAL(20,2),
    recommended_monthly_cost DECIMAL(20,2),
    monthly_savings DECIMAL(20,2),
    savings_percentage DECIMAL(5,2),
    priority VARCHAR(20),                 -- 'high', 'medium', 'low'
    effort_level VARCHAR(20),              -- 'low', 'medium', 'high'
    implementation_days INT,
    roi_months DECIMAL(5,2),
    status VARCHAR(50),                   -- 'proposed', 'approved', 'implemented', 'rejected'
    created_at TIMESTAMP,
    implemented_at TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant(id)
);
```

### 2.3 API Endpoints

```
GET /api/ai-services
  Get all AI services and current costs
  Params: tenant_id, days=30, service_filter
  Returns: {
    total_cost: 26380,
    services: [
      {
        name: 'Claude 3 Opus',
        provider: 'aws',
        status: 'active',
        cost_30d: 12450,
        input_tokens_30d: 2500000000,
        output_tokens_30d: 400000000,
        requests_30d: 13500,
        cost_per_request: 27.67,
        moy_trend: 8,
        budget: 15000,
        budget_status: 'warning'
      },
      ...
    ]
  }

POST /api/ai-services/{service}/budget
  Set budget for an AI service
  Body: { monthly_budget: 15000, alert_threshold_pct: 80 }
  Returns: { service, budget, alert_threshold }

GET /api/ai-services/{service}/usage-trend
  Get token usage trend over time
  Params: days=30
  Returns: {
    dates: ['2026-04-09', ...],
    input_tokens: [1800000000, ...],
    output_tokens: [300000000, ...],
    costs: [380, ...]
  }

GET /api/ai-services/{service}/optimization-recommendations
  Get cost optimization recommendations
  Returns: [
    {
      id: 'rec-123',
      title: 'Switch code review to Claude 3 Haiku',
      monthly_savings: 1650,
      priority: 'high',
      effort_days: 1
    },
    ...
  ]

POST /api/ai-services/{service}/recommendations/{rec_id}/implement
  Mark a recommendation as implemented
  Body: { notes: 'Integrated on 2026-05-08' }
  Returns: { recommendation, status: 'implemented', cost_actual: 1620 }

GET /api/ai-services/anomalies
  Get detected cost anomalies
  Params: days=30, severity=critical
  Returns: [
    {
      id: 'anomaly-456',
      service: 'Claude 3 Opus',
      detected_at: '2026-05-08T22:00:00Z',
      baseline_cost: 2100,
      anomaly_cost: 6300,
      severity: 'critical',
      action_taken: 'suspended'
    },
    ...
  ]

POST /api/ai-services/anomalies/{anomaly_id}/investigate
  Mark anomaly as investigated
  Body: { status: 'resolved', notes: 'Bug in data pipeline, fixed' }
```

### 2.4 Frontend Components

```jsx
// AICostDashboard.jsx

import React, { useState, useEffect } from 'react';
import { LineChart, BarChart, PieChart, Area } from 'recharts';
import axios from 'axios';

export function AICostDashboard() {
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [trends, setTrends] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [anomalies, setAnomalies] = useState([]);

  useEffect(() => {
    // Fetch AI service data
    const fetchData = async () => {
      const [svc, rec, anom] = await Promise.all([
        axios.get('/api/ai-services', {
          params: { tenant_id: 'tenant-demo', days: 30 }
        }),
        axios.get('/api/ai-services/recommendations'),
        axios.get('/api/ai-services/anomalies', {
          params: { severity: 'critical' }
        })
      ]);
      setServices(svc.data.services);
      setRecommendations(rec.data);
      setAnomalies(anom.data);
    };
    fetchData();
  }, []);

  const handleSelectService = async (service) => {
    setSelectedService(service);
    const trend = await axios.get(`/api/ai-services/${service.name}/usage-trend`);
    setTrends(trend.data);
  };

  return (
    <div className="ai-cost-dashboard">
      <h1>AI Cost Dashboard</h1>

      {/* Service Inventory */}
      <section className="service-inventory">
        <h2>Active AI Services</h2>
        <div className="service-cards">
          {services.map(service => (
            <div key={service.name} 
                 className="service-card"
                 onClick={() => handleSelectService(service)}>
              <h3>{service.name}</h3>
              <div className="cost">${service.cost_30d.toFixed(0)}</div>
              <div className="trend">
                {service.moy_trend > 0 ? '↑' : '↓'} {Math.abs(service.moy_trend)}%
              </div>
              <div className="budget-bar">
                <div style={{ width: `${Math.min(100, (service.cost_30d / service.budget) * 100)}%` }} />
              </div>
              <div className="budget-text">
                ${service.cost_30d.toFixed(0)} of ${service.budget.toFixed(0)}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Service Detail */}
      {selectedService && (
        <section className="service-detail">
          <h2>{selectedService.name} - Detailed Analysis</h2>
          
          {/* Cost Breakdown */}
          <div className="cost-breakdown">
            <div className="breakdown-item">
              <div className="label">Input Tokens</div>
              <div className="value">${(selectedService.cost_30d * 0.60).toFixed(0)}</div>
              <div className="percentage">60%</div>
            </div>
            {/* ... more breakdown items ... */}
          </div>

          {/* Usage Trend Chart */}
          <div className="usage-trend">
            <LineChart data={trends}>
              {/* Chart configuration */}
            </LineChart>
          </div>

          {/* Recommendations */}
          <div className="recommendations">
            <h3>Optimization Opportunities</h3>
            {recommendations.map(rec => (
              <div key={rec.id} className={`recommendation ${rec.priority}`}>
                <h4>{rec.title}</h4>
                <p>{rec.description}</p>
                <div className="metrics">
                  <span>Savings: ${rec.monthly_savings}</span>
                  <span>Effort: {rec.effort_days} days</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Anomalies */}
      <section className="anomalies">
        <h2>Cost Anomalies (Last 30 Days)</h2>
        {anomalies.map(anomaly => (
          <div key={anomaly.id} className={`anomaly ${anomaly.severity}`}>
            <h3>{anomaly.service}</h3>
            <p>{anomaly.application_name}</p>
            <div className="cost-spike">
              Normal: ${anomaly.baseline_cost} | Spike: ${anomaly.anomaly_cost}
            </div>
            <div className="action">Action: {anomaly.action_taken}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
```

---

## Summary

This specification provides:

1. **RBAC Implementation**: 6-role hierarchy, 4-level scoping, database schema, API enforcement, and frontend integration
2. **AI Cost Dashboard**: Comprehensive UI design showing services, token economics, optimization recommendations, budget tracking, and anomaly detection
3. **Data Models**: Database tables for tracking AI service costs, budgets, anomalies, pricing, and recommendations
4. **APIs**: RESTful endpoints for AI service data, budgets, trends, and anomalies
5. **Frontend Components**: React components for dashboard visualization

**Estimated Development Effort**: 
- RBAC: 4 weeks (database, API, frontend, testing)
- AI Dashboard: 3 weeks (backend data pipeline, frontend components, visualizations)
- **Total: 7 weeks** for both features
