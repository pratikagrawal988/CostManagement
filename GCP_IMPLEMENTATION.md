# GCP Cost Integration Implementation

## Overview

This document describes the Google Cloud Platform (GCP) cost integration added to the FinOps platform, enabling organizations to aggregate GCP cost data from BigQuery alongside AWS and Azure into a unified FOCUS-aligned framework.

## Architecture

### Data Flow

```
GCP BigQuery (gcp_billing_export_v1)
         ↓
   gcp_ingest job (5m poll)
         ↓
   GcpCostIngestConfig (credentials & project info)
         ↓
   CostDetail table (raw GCP data)
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

**GcpCostIngestConfig**
- Stores GCP project, billing account, and Service Account credentials
- Manages BigQuery dataset and table references
- Tracks connection status and sync history
- Fields:
  - `gcp_project_id`: GCP project ID
  - `service_account_email`: Service account email
  - `service_account_key_encrypted`: OAuth JSON key
  - `billing_account_id`: GCP billing account ID
  - `bq_dataset_id`: BigQuery dataset (usually "billing_export")
  - `bq_table_id`: BigQuery table (usually "gcp_billing_export_v1")
  - `export_frequency`: Daily or Monthly
  - `data_source`: standard or detailed
  - `last_synced_at`: Last successful data retrieval

#### 2. Ingestion Engine (`gcp_jobs.py`)

**run_gcp_ingest()**
- Main entry point called every 5 minutes
- Fetches all enabled GcpCostIngestConfig records
- Processes each GCP project sequentially
- Records job run status and metrics

**_ingest_for_gcp_config()**
- Per-project ingestion logic
- Authenticates with Service Account JSON key
- Queries BigQuery for cost data since last sync
- Parses results and upserts to CostDetail
- Updates last_synced_at timestamp

**get_bigquery_client()**
- Service Account authentication
- Creates authenticated BigQuery client
- Validates JSON key format
- Error handling for failed authentication

**_parse_gcp_results()**
- Transforms BigQuery result rows to CostDetail records
- Extracts dimensions: ServiceName, ResourceLocation
- Extracts costs: PreTaxCost, UsageAmount
- Handles GCP labels as tags
- Batch insert with row-by-row fallback for integrity errors

**run_gcp_focus_transform()**
- Called by main focus_transform job
- Transforms GCP CostDetail → FocusCost
- Sets invoice_issuer = "gcp"
- Applies service category mappings from ProductCategory
- Creates daily cost aggregations

#### 3. API Endpoints (`routes_gcp.py`)

**GET /api/gcp/ingest-config**
- List all GCP cost configurations
- Filter by tenant_id (optional)
- Returns connection status and last sync time

**POST /api/gcp/ingest-config**
- Create new GCP configuration
- Validates service account key JSON format
- Stores key encrypted (TODO: use Secret Manager in production)
- Returns config_id for reference

**PATCH /api/gcp/ingest-config/{id}**
- Update configuration settings
- Can modify export frequency, data source, enabled status
- Validates input values
- Returns updated_at timestamp

**POST /api/gcp/test-connection**
- Tests Service Account authentication and BigQuery access
- Runs test query on billing table
- Updates test_status and test_message
- Used in admin UI to validate credentials

#### 4. Seed Data (`seed_cost_mappings.py`)

Added GCP service mappings:

**seed_gcp_product_categories()**
- Compute: Compute Engine, App Engine, Cloud Functions, Cloud Run, GKE
- Storage: Cloud Storage, Firestore, Cloud Datastore, Cloud SQL
- Database: Cloud SQL, Firestore, Spanner, Bigtable, Memorystore
- Networking: CDN, Load Balancing, Interconnect, VPN, NAT
- AI/ML: Vertex AI, BigQuery ML, AI Platform, Vision, NLP, Translation, Speech
- Analytics: BigQuery, Dataflow, Dataproc, Data Fusion

**seed_gcp_ai_classifications()**
- Vertex AI: PaLM models (input/output tokens)
- Vision API: Detection and analysis requests
- Translation API: Character-based pricing
- Speech-to-Text: Duration-based pricing
- BigQuery ML: Data-based pricing

## Setup Guide

### Prerequisites

1. GCP project with Cloud Billing enabled
2. BigQuery dataset with gcp_billing_export_v1 table
3. Service Account with BigQuery Data Viewer role
4. Service Account JSON key file

### Step 1: Enable Cloud Billing Export to BigQuery

```bash
# In GCP Console:
# 1. Go to Billing → Billing Exports
# 2. Create new BigQuery export
# 3. Select dataset (or create "billing_export")
# 4. Export destination: gcp_billing_export_v1
# 5. Enable daily export
```

### Step 2: Create Service Account

```bash
PROJECT_ID="your-gcp-project"
SA_NAME="finops-service-account"

# Create service account
gcloud iam service-accounts create $SA_NAME \
  --project=$PROJECT_ID \
  --display-name="FinOps Cost Ingestion"

# Get service account email
SA_EMAIL=$(gcloud iam service-accounts list --project=$PROJECT_ID \
  --filter="displayName:$SA_NAME" --format='value(email)')

echo $SA_EMAIL
```

### Step 3: Grant BigQuery Permissions

```bash
# Grant BigQuery Data Viewer role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataViewer"

# Grant BigQuery Job User role (to run queries)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.jobUser"
```

### Step 4: Create and Download Service Account Key

```bash
# Create JSON key
gcloud iam service-accounts keys create ~/finops-key.json \
  --iam-account=$SA_EMAIL

# View key (for configuration)
cat ~/finops-key.json

# Keep this file secure!
```

### Step 5: Create Configuration via Admin UI

1. Navigate to **Admin Panel → GCP Cost Setup**
2. Click **+ New Configuration**
3. Enter:
   - **GCP Project ID**: Your project ID
   - **Service Account Email**: `finops-service-account@project.iam.gserviceaccount.com`
   - **Service Account Key**: Paste JSON from ~/finops-key.json
   - **Billing Account ID**: Your billing account ID (from GCP Billing console)
   - **BigQuery Dataset**: `billing_export` (or custom)
   - **BigQuery Table**: `gcp_billing_export_v1` (or custom)
   - **Export Frequency**: Daily (recommended) or Monthly
   - **Data Source**: standard or detailed
4. Click **Create Configuration**

### Step 6: Test Connection

1. Click **Test Connection** button on the configuration
2. Monitor **Job Status → gcp_ingest** for results
3. Verify access to BigQuery table in Cloud Logging

### Step 7: Monitor Ingestion

The gcp_ingest job runs every 5 minutes:
- Queries BigQuery for cost data since last sync
- Inserts new records into CostDetail table
- Updates last_synced_at and test_status

View job history in **Admin Panel → Job Status & History**:
- **gcp_ingest**: BigQuery polling and data ingestion
- **focus_transform**: Transformation to FOCUS schema

## Data Schema Mapping

### BigQuery gcp_billing_export_v1 → CostDetail

| BigQuery Field | CostDetail Field | Notes |
|---|---|---|
| service.description | service | GCP service name |
| sku.description | sku | SKU description |
| COALESCE(location.location, resource.location) | region | Geographic location |
| usage.amount_in_pricing_units | usage_quantity | Usage amount |
| cost | cost_after_discount | Total cost |
| project.id | account_id | GCP project ID |
| labels | tags | GCP resource labels |

### CostDetail → FocusCost Transformation

FOCUS fields populated during focus_transform job:
- `invoice_issuer`: "gcp"
- `service_name`: From BigQuery ServiceName
- `service_category`: From ProductCategory mapping
- `billing_period_start`: From usage_start_date
- `usage_quantity`: From usage amount
- `billed_cost`: From cost
- `tags`: GCP labels + metadata

## Integration with Dashboards

GCP costs are immediately visible in all persona dashboards:

1. **Finance Portal**
   - Total spend includes GCP (invoice_issuer = "gcp")
   - Trend chart shows AWS vs Azure vs GCP
   - Top drivers include GCP services

2. **FinOps Analytics**
   - Optimization recommendations analyze GCP services
   - AI service costs include Vertex AI, Vision API
   - Category breakdown includes GCP-specific categories

3. **Team Cost Dashboard**
   - Allocation includes GCP projects as team identifiers
   - Budget tracking across all clouds

4. **Executive Summary**
   - Forecast includes projected GCP spend
   - Annual spend and MoM growth include GCP

## Cost Aggregation

Daily cost aggregations are created automatically:
- Grouped by (date, service, category, region)
- Summed across all GCP projects in tenant
- Used for high-performance dashboard queries

Example aggregation:
```json
{
  "date": "2025-05-09",
  "service": "Compute Engine",
  "category": "Compute",
  "region": "us-central1",
  "total_cost": 850.25,
  "total_usage": 744.0,
  "unit_count": 8,
  "resource_count": 3
}
```

## Error Handling & Recovery

### Connection Failures

1. **Authentication Error**
   - Check service account email and key validity
   - Verify key hasn't expired
   - Test in gcloud: `gcloud auth activate-service-account --key-file=key.json`

2. **BigQuery Permission Error**
   - Verify BigQuery Data Viewer and Job User roles
   - Check dataset exists and is accessible
   - Test query: `bq ls --project_id=$PROJECT_ID billing_export`

3. **Invalid BigQuery Table**
   - Verify billing export is enabled
   - Check table name matches (usually "gcp_billing_export_v1")
   - Wait 24 hours for first export if just enabled

### Data Quality Issues

1. **Missing Data**
   - Verify BigQuery billing export is enabled
   - Check table contains data: `bq query "SELECT COUNT(*) FROM billing_export.gcp_billing_export_v1"`
   - Wait 24 hours for first daily export

2. **Duplicates**
   - Detected automatically by unique constraints
   - BigQuery API is idempotent; safe to re-query same period
   - Focus_transform handles upserts automatically

3. **Cost Discrepancies**
   - Verify data_source setting (standard vs detailed)
   - Check if export includes all services/projects
   - Verify no exclusion filters are applied

## Configuration Reference

### Schedule

```yaml
gcp_ingest:
  interval: 5m              # Poll BigQuery every 5 minutes
  batch_size: 100           # Max rows per batch
  retry_on_failure: true    # Auto-retry on transient failures
  warm_retention: 365 days  # Keep detailed records 1 year
  cold_retention: 730 days  # Archive older records
```

### BigQuery Query

```sql
SELECT
    CAST(SUBSTR(usage_start_time, 1, 10) AS STRING) as usage_date,
    service.description as service_name,
    sku.description as sku_description,
    COALESCE(location.location, resource.location, 'UNKNOWN') as resource_location,
    usage.amount_in_pricing_units as usage_amount,
    cost as cost_amount,
    project.id as project_id,
    labels
FROM `{project_id}.{dataset_id}.{table_id}`
WHERE CAST(SUBSTR(usage_start_time, 1, 10) AS DATE) >= '{start_date}'
  AND cost > 0
LIMIT 100000
```

## Security Considerations

### Credential Management

⚠️ **IMPORTANT**: Current implementation stores service account key as plaintext in database.

**TODO for Production:**
1. Encrypt keys with Secret Manager
2. Use short-lived credentials (1 hour)
3. Rotate keys quarterly
4. Audit access via Cloud Audit Logs

### Access Control

- Service Account needs **BigQuery Data Viewer** and **BigQuery Job User** roles
- No write permissions required
- Scope to specific project (not organization)

### Audit Trail

All BigQuery queries are logged:
- Enable Cloud Audit Logs in GCP Console
- Filter by Service: "BigQuery API"
- Review in GCP > Monitoring > Logs

## Troubleshooting

### Problem: "Invalid JSON key" error

**Solution**: Verify service account key format:
```bash
# Key must be valid JSON with these fields
cat finops-key.json | jq '.type, .project_id, .private_key_id'

# Should output: "service_account", your project, and a key ID
```

### Problem: "Permission denied" error

**Solution**: Grant required roles:
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.jobUser"
```

### Problem: "Table not found" error

**Solution**: Verify BigQuery export is configured:
1. GCP Console > Billing > Billing Exports
2. Check "Export to BigQuery" is enabled
3. Verify dataset name matches config (usually "billing_export")
4. Wait 24 hours for first export

### Problem: No data ingested after 24 hours

**Solution**: Check:
1. Is BigQuery export enabled and generating data?
2. Does service account have read permissions?
3. Are there actual charges in the period?
4. Check job status in Admin Panel for error messages

## Performance Tuning

### Large GCP Deployments (>100M rows/month)

1. Increase batch_size in config:
```yaml
gcp_ingest:
  batch_size: 500  # From default 100
```

2. Query only recent data:
```bash
# In _ingest_for_gcp_config, only query last 3 days
timeframe_start = (config.last_synced_at or utcnow() - timedelta(days=3)).date()
```

3. Consider BigQuery archival:
- Export to Cloud Storage for long-term retention
- Import historical data via batch job

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

1. Single Project per Configuration
   - Use multiple configs for multi-project scenarios
2. Standard BigQuery Table Only
   - Does not support custom schemas
3. No Cloud Billing API Support
   - Only BigQuery export method

### Planned Enhancements

- [ ] Multi-project rollup configuration
- [ ] Cloud Billing API integration (alternative)
- [ ] GCP Committed Use Discounts allocation
- [ ] Multi-cloud cost optimization recommendations
- [ ] GCP-specific anomaly detection

## API Examples

### Create GCP Configuration

```bash
curl -X POST "http://localhost:8000/api/gcp/ingest-config" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-demo",
    "gcp_project_id": "my-gcp-project",
    "service_account_email": "finops-sa@my-gcp-project.iam.gserviceaccount.com",
    "service_account_key": "{\"type\": \"service_account\", ...}",
    "billing_account_id": "123456-789ABC-DEF012",
    "bq_dataset_id": "billing_export",
    "bq_table_id": "gcp_billing_export_v1",
    "export_frequency": "Daily",
    "data_source": "standard",
    "enabled": true
  }'
```

### Test Connection

```bash
curl -X POST "http://localhost:8000/api/gcp/test-connection?config_id=abc123"
```

### List Configurations

```bash
curl "http://localhost:8000/api/gcp/ingest-config?tenant_id=tenant-demo"
```

### Get GCP Costs

```bash
curl "http://localhost:8000/api/cost/daily?tenant_id=tenant-demo&service=Compute%20Engine"
```

## References

- [GCP Billing Export to BigQuery](https://cloud.google.com/billing/docs/how-to/export-data-bigquery)
- [BigQuery Cost Table Schema](https://cloud.google.com/billing/docs/how-to/export-data-bigquery-tables)
- [Service Account Setup](https://cloud.google.com/docs/authentication/production)
- [BigQuery Client Libraries](https://cloud.google.com/bigquery/docs/reference/libraries-overview)
- [FOCUS Specification](https://focus.finops.org/)
- [GCP IAM Roles](https://cloud.google.com/iam/docs/understanding-roles)
