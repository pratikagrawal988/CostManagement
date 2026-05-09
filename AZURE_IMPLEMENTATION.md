# Azure Cost Integration Implementation

## Overview

This document describes the Azure Cost Management integration added to the FinOps platform, enabling organizations to aggregate and normalize Azure cost data alongside AWS and GCP data into the FOCUS specification.

## Architecture

### Data Flow

```
Azure Cost Management API
         ↓
   azure_ingest job (5m poll)
         ↓
   AzureCostIngestConfig (credentials & subscription)
         ↓
   CostDetail table (raw Azure data)
         ↓
   focus_transform job (1h)
         ↓
   FocusCost table (FOCUS-normalized)
         ↓
   CostAggregation table (daily summaries)
         ↓
   Cost Dashboards & Reports
```

### Components Added

#### 1. Database Models (`models.py`)

**AzureCostIngestConfig**
- Stores Azure subscription and Service Principal credentials
- Manages connection configuration and testing
- Fields:
  - `azure_subscription_id`: Target subscription GUID
  - `azure_tenant_id`: Azure AD tenant for authentication
  - `client_id`: Service Principal app ID
  - `client_secret_encrypted`: OAuth credentials
  - `export_scope`: Cost Management API scope
  - `export_frequency`: Daily or Monthly exports
  - `data_source`: actual_cost or amortized_cost
  - `last_synced_at`: Last successful data retrieval
  - `test_status`: Connection test result

#### 2. Ingestion Engine (`azure_jobs.py`)

**run_azure_ingest()**
- Main entry point called every 5 minutes
- Fetches all enabled AzureCostIngestConfig records
- Processes each Azure subscription sequentially
- Records job run status and metrics

**_ingest_for_azure_config()**
- Per-subscription ingestion logic
- Authenticates with Azure Cost Management API using Service Principal
- Queries cost data from last sync date forward
- Parses API response and upserts to CostDetail
- Updates last_synced_at timestamp

**get_azure_access_token()**
- OAuth 2.0 authentication with Azure AD
- Service Principal (client credentials flow)
- 1-hour token validity
- Error handling for failed authentication

**_parse_azure_cost_response()**
- Transforms Azure API JSON response to CostDetail records
- Extracts dimensions: ServiceName, ResourceType, ResourceGroup, Location
- Extracts values: PreTaxCost, UsageQuantity
- Handles duplicates via unique constraints
- Batch insert with row-by-row fallback for integrity errors

**run_azure_focus_transform()**
- Called by main focus_transform job
- Transforms Azure CostDetail → FocusCost
- Sets invoice_issuer = "azure"
- Applies service category mappings from ProductCategory
- Creates daily cost aggregations

#### 3. API Endpoints (`routes_azure.py`)

**GET /api/azure/ingest-config**
- List all Azure cost configurations
- Filter by tenant_id (optional)
- Returns connection status and last sync time

**POST /api/azure/ingest-config**
- Create new Azure configuration
- Validates subscription/tenant ID format (GUID)
- Encrypts client secret (TODO: use Key Vault in production)
- Returns config_id for reference

**PATCH /api/azure/ingest-config/{id}**
- Update configuration settings
- Can modify export frequency, data source, enabled status
- Validates input values
- Returns updated_at timestamp

**POST /api/azure/test-connection**
- Tests Service Principal authentication
- Updates test_status and test_message
- Used in admin UI to validate credentials before ingestion starts

#### 4. Seed Data (`seed_cost_mappings.py`)

Added Azure service mappings:

**seed_azure_product_categories()**
- Compute: VM, App Service, Container Instances, AKS, Functions, Batch
- Storage: Blob, File Share, Managed Disks, Archive
- Database: SQL, Cosmos DB, MySQL, PostgreSQL, Redis
- Networking: VPN, App Gateway, Load Balancer, Bandwidth, ExpressRoute
- AI/ML: Cognitive Services, Machine Learning, Vision, Speech, Language

**seed_azure_ai_classifications()**
- Azure OpenAI: GPT-4 (input/output tokens)
- Computer Vision: Image analysis, OCR
- Speech: Speech-to-Text, Text-to-Speech
- Machine Learning: ML Instance compute

## Setup Guide

### Prerequisites

1. Azure subscription with Cost Management enabled
2. Service Principal with Cost Management Reader role
3. Client secret generated for the Service Principal

### Step 1: Create Service Principal

```bash
# Create Service Principal
az ad sp create-for-rbac --name "FinOps-ServiceAccount"

# Output example:
# {
#   "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
#   "displayName": "FinOps-ServiceAccount",
#   "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
#   "tenant": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyyyy"
# }
```

Save the `appId` (client_id) and `password` (client_secret), and `tenant` (azure_tenant_id).

### Step 2: Grant Cost Management Reader Role

```bash
SUBSCRIPTION_ID="zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"
RESOURCE_GROUP="FinOps"
SP_OBJECT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# Grant Cost Management Reader role
az role assignment create \
  --scope "/subscriptions/$SUBSCRIPTION_ID" \
  --role "Cost Management Reader" \
  --assignee-object-id $SP_OBJECT_ID \
  --assignee-principal-type ServicePrincipal
```

### Step 3: Create Configuration via Admin UI

1. Navigate to **Admin Panel → Azure Cost Setup**
2. Click **+ New Configuration**
3. Enter:
   - **Azure Subscription ID**: `zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz`
   - **Azure Tenant ID**: `yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyyyy`
   - **Client ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - **Client Secret**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Export Frequency**: Daily (recommended) or Monthly
   - **Data Source**: actual_cost or amortized_cost
4. Click **Create Configuration**

### Step 4: Test Connection

1. Click **Test Connection** button on the configuration
2. Monitor **Job Status → azure_ingest** for results
3. Check CloudTrail for API calls and test_status field

### Step 5: Monitor Ingestion

The azure_ingest job runs every 5 minutes:
- Fetches cost data from 24 hours before last sync
- Inserts new records into CostDetail table
- Updates last_synced_at and test_status

View job history in **Admin Panel → Job Status & History**:
- **azure_ingest**: API polling and data ingestion
- **focus_transform**: Transformation to FOCUS schema

## Data Schema Mapping

### Azure API Response → CostDetail

| Azure Field | CostDetail Field | Notes |
|-------------|------------------|-------|
| ServiceName | service | Azure service name |
| ResourceType | sku | Resource type (e.g., "Microsoft.Compute/virtualMachines") |
| ResourceGroup | resource_id | Azure resource group |
| ResourceLocation | region | Azure region |
| PreTaxCost | cost_after_discount | Total cost before taxes |
| UsageDate | usage_start_date | YYYY-MM-DD |
| usage_account_id | account_id | Azure subscription ID |
| Sourced_from | sourced_from | "azure" (literal) |

### CostDetail → FocusCost Transformation

FOCUS fields populated during focus_transform job:
- `invoice_issuer`: "azure"
- `service_name`: From Azure ServiceName
- `service_category`: From ProductCategory mapping
- `billing_period_start`: From usage_start_date
- `usage_quantity`: From Azure UsageQuantity or 0
- `billed_cost`: From cost_after_discount
- `tags`: Extracted from ResourceGroup and ResourceType

## Integration with Dashboards

Azure costs are immediately visible in all persona dashboards:

1. **Finance Portal**
   - Total spend includes Azure (invoice_issuer = "azure")
   - Trend chart shows Azure vs AWS vs GCP
   - Top drivers include Azure services

2. **FinOps Analytics**
   - Optimization recommendations analyze Azure services
   - AI service costs include Azure OpenAI, Cognitive Services
   - Category breakdown includes Azure-specific categories

3. **Team Cost Dashboard**
   - Allocation includes Azure resource groups as team identifiers
   - Budget tracking across all clouds

4. **Executive Summary**
   - Forecast includes projected Azure spend
   - Annual spend and MoM growth include Azure

## Cost Aggregation

Daily cost aggregations are created automatically:
- Grouped by (date, service, category, region)
- Summed across all Azure subscriptions in tenant
- Used for high-performance dashboard queries

Example aggregation:
```json
{
  "date": "2025-05-09",
  "service": "Virtual Machines",
  "category": "Compute",
  "region": "eastus",
  "total_cost": 1250.50,
  "total_usage": 744.0,
  "unit_count": 12,
  "resource_count": 5
}
```

## Error Handling & Recovery

### Connection Failures

1. **Authentication Error**
   - Check client_id and client_secret validity
   - Verify Service Principal still exists in Azure AD
   - Test in Azure CLI: `az account get-access-token`

2. **API Rate Limiting**
   - Azure Cost Management has rate limits
   - Backoff with exponential retry (3x with 30s, 60s, 120s delays)
   - Contact Azure support for quota increase if persistent

3. **Invalid Subscription**
   - Verify subscription_id format (GUID)
   - Ensure Service Principal has access to subscription
   - Test: `az account show --subscription $SUBSCRIPTION_ID`

### Data Quality Issues

1. **Missing Data**
   - Check if cost exports are enabled in Azure Billing console
   - Allow 24 hours for first export to generate
   - Verify data_source setting matches export type

2. **Duplicates**
   - Detected automatically by unique constraint on CostDetail
   - Azure API is idempotent; safe to re-ingest same period
   - Focus_transform handles upserts automatically

3. **Cost Discrepancies**
   - Use actual_cost for immediate charges, amortized_cost for reservations
   - Verify tax treatment: PreTaxCost vs post-tax amounts
   - Check if subscription includes management fees

## Configuration Reference

### Schedule

```yaml
azure_ingest:
  interval: 5m              # Poll every 5 minutes
  batch_size: 100           # Max records per batch
  retry_on_failure: true    # Auto-retry on transient failures
  warm_retention: 365 days  # Keep detailed records 1 year
  cold_retention: 730 days  # Archive older records
```

### Environment Variables

```bash
# Optional: override default settings
AZURE_INGEST_ENABLED=true          # Enable/disable job
AZURE_API_TIMEOUT=60               # API timeout seconds
AZURE_MAX_RETRIES=3                # Max retry attempts
COST_INGEST_PARALLEL_CONFIGS=3     # Parallel Azure configs
```

## Security Considerations

### Credential Management

⚠️ **IMPORTANT**: Current implementation stores client_secret as plaintext in database.

**TODO for Production:**
1. Encrypt secrets with Key Vault
2. Use managed identities instead of Service Principal
3. Rotate secrets quarterly
4. Audit access via Azure Audit Logs

### Access Control

- Service Principal needs **Cost Management Reader** role only
- No write permissions required
- Scope to specific subscription (not entire tenant)

### Audit Trail

Azure Cost Management API calls are logged:
- Enable Activity Log in Azure portal
- Filter by Service: "CostManagement"
- Review in Azure > Monitor > Activity Log

## Troubleshooting

### Problem: "Invalid tenant ID" error

**Solution**: Verify azure_tenant_id format is correct GUID:
```bash
# List your tenant ID
az account list --query '[0].tenantId'

# Output: "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyyyy"
```

### Problem: "The caller is not authorized" error

**Solution**: Grant Cost Management Reader role:
```bash
az role assignment create \
  --role "Cost Management Reader" \
  --assignee $CLIENT_ID
```

### Problem: No data ingested after 24 hours

**Solution**: Check:
1. Is cost export enabled in Azure Billing console?
2. Are there any charges in the period being queried?
3. Does the Service Principal have the correct role?
4. Check job status in Admin Panel for error messages

### Problem: Costs appear in raw data but not in dashboards

**Solution**: Run focus_transform manually:
```bash
curl -X POST http://localhost:8000/api/cost/status?job_name=focus_transform

# Wait for hourly job to run
# Or trigger manually if needed
```

## Performance Tuning

### Large Subscriptions (>1M records/month)

1. Increase batch_size in config:
```yaml
azure_ingest:
  batch_size: 500  # From default 100
```

2. Extend sync window to reduce API calls:
```bash
# Sync every 24h instead of 5m
# Requires changing schedule interval
```

3. Consider using CSV export instead of API:
- Allows bulk historical ingestion
- Better for initial data load
- Use `/api/azure/import-csv` endpoint (future)

### Cost Aggregation Performance

Aggregations created during focus_transform are indexed:
- `idx_cost_agg_tenant_date`: Fast date-range queries
- `idx_cost_agg_service`: Service filtering
- `idx_cost_agg_category`: Category breakdown

For large datasets (>100M records), consider:
1. Partition aggregation table by month
2. Add materialized views for top queries
3. Archive older data to cold storage

## Limitations & Roadmap

### Current Limitations

1. Single Azure subscription per configuration
   - Use multiple configs for multi-subscription scenarios
2. No reservation/benefit handling
   - Set data_source to amortized_cost for proper costs
3. No Azure Stack or Government Cloud support
   - Requires separate API endpoint configuration

### Planned Enhancements

- [ ] CSV export import (bulk historical data)
- [ ] Multi-subscription rollup configuration
- [ ] Azure reservations cost allocation
- [ ] GCP BigQuery integration (parallel to Azure)
- [ ] Cost anomaly detection across clouds
- [ ] Chargeback reporting with showback
- [ ] RI/commitment recommendations
- [ ] Reserved Instance purchase analysis

## API Examples

### Create Azure Configuration

```bash
curl -X POST "http://localhost:8000/api/azure/ingest-config" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-demo",
    "azure_subscription_id": "12345678-1234-1234-1234-123456789012",
    "azure_tenant_id": "abcdef01-2345-6789-abcd-ef0123456789",
    "client_id": "fedcba98-7654-3210-fedc-ba9876543210",
    "client_secret": "your_client_secret_here",
    "export_frequency": "Daily",
    "data_source": "actual_cost",
    "enabled": true
  }'
```

### Test Connection

```bash
curl -X POST "http://localhost:8000/api/azure/test-connection?config_id=abc123"
```

### List Configurations

```bash
curl "http://localhost:8000/api/azure/ingest-config?tenant_id=tenant-demo"
```

### Get Azure Costs

```bash
curl "http://localhost:8000/api/cost/daily?tenant_id=tenant-demo&category=Compute"
```

## References

- [Azure Cost Management REST API](https://learn.microsoft.com/en-us/rest/api/cost-management/)
- [Azure Service Principal Setup](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-demand)
- [FOCUS Specification](https://focus.finops.org/)
- [Azure Role-Based Access Control](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
