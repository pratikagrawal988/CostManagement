# AWS CUR Parser & Ingestion Job - Implementation Guide

## Overview

**Phase 2** of the Multi-Cloud Cost Aggregation system implements the **AWS Cost and Usage Report (CUR) ingestion job**, which:

1. **Polls S3 every 5 minutes** for new AWS CUR Parquet files
2. **Detects new files** by comparing modification timestamps with `last_tested_at`
3. **Downloads and decompresses** Parquet files (with gzip support)
4. **Parses CUR data** with proper decimal precision for financial accuracy
5. **Upserts to CostDetail table** using idempotent logic (no full table replacements)
6. **Handles errors gracefully** and continues processing other files/configs
7. **Records job status** in the `JobRun` table for monitoring and debugging

---

## Architecture

### Job Flow Diagram

```
start_scheduler()
    └── run_cost_ingest() [every 5 minutes]
        ├── Get all enabled CostIngestConfig records
        └── For each config:
            ├── Assume AWS role with external ID (cross-account access)
            ├── List S3 objects in configured bucket/prefix
            ├── For each new Parquet file (by LastModified timestamp):
            │   ├── Download from S3
            │   ├── Decompress (if .gz)
            │   ├── Parse with pandas.read_parquet()
            │   └── Upsert to CostDetail table
            ├── Update config.last_tested_at
            └── Record JobRun with status, file count, inserted/updated counts
```

### Components

#### 1. **CostIngestConfig Model** (models.py)
Stores per-tenant AWS CUR configuration:

```python
class CostIngestConfig(Base):
    __tablename__ = "cost_ingest_configs"
    
    id: str  # Primary key
    tenant_id: str  # Multi-tenant isolation
    s3_bucket: str  # e.g., "my-billing-bucket"
    s3_prefix: str  # e.g., "AWSLogs/123456789012/costs"
    aws_role_arn: str  # Cross-account role to assume
    aws_external_id: str  # External ID for role assumption
    enabled: bool  # Enable/disable ingestion
    last_tested_at: datetime  # Timestamp of last successful poll
    test_status: str  # "pending", "success", "failed"
    test_message: str  # Error details if failed
```

**Role Assumption Flow:**
- Application has a service role with `sts:AssumeRole` permission
- Customer's AWS account has a cross-account role with:
  - ExternalId matching the configured value
  - Permissions to read from the CUR S3 bucket
  - Trust relationship allowing the application's role

#### 2. **CostDetail Model** (models.py)
Stores raw AWS CUR data in native format:

```python
class CostDetail(Base):
    __tablename__ = "cost_details"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "account_id", "service", "sku", "region", 
            "usage_start_date", name="uq_cost_detail"
        ),
    )
    
    # Key fields
    tenant_id: str  # Multi-tenant
    account_id: str  # AWS account ID
    service: str  # AWS service name (EC2, S3, RDS, etc.)
    service_code: str  # Service code (AmazonEC2, AmazonS3, etc.)
    sku: str  # Pricing SKU
    region: str  # AWS region
    usage_start_date: str  # YYYY-MM-DD
    
    # Financial precision with Decimal
    usage_quantity: Decimal  # Numeric(20, 10)
    rate: Decimal  # Numeric(20, 10)
    cost_before_discount: Decimal  # Numeric(20, 10)
    discount: Decimal  # Numeric(20, 10)
    cost_after_discount: Decimal  # Numeric(20, 10)
    cost_with_tax: Decimal  # Numeric(20, 10)
    
    # Metadata
    tags: dict  # JSON column for resource tags
    resource_id: str  # AWS resource ID
    sourced_from: str  # "cur" or "focus_export"
    parsed_at: datetime  # When record was parsed
```

**Unique Constraint Behavior:**
- The unique constraint on `(tenant_id, account_id, service, sku, region, usage_start_date)` enables **idempotent upserts**
- Duplicate rows (same day, same service/SKU/region) are updated instead of duplicated
- No need for full table replacements or "delete then insert" logic

---

## Implementation Details

### 1. **Main Job Function: `run_cost_ingest()`**

```python
async def run_cost_ingest(settings: Settings) -> dict[str, Any]:
```

**Behavior:**
1. Creates a `JobRun` record with status "running"
2. Queries all enabled `CostIngestConfig` records
3. For each config, calls `_ingest_for_config()` to process that tenant
4. Aggregates results: total files, inserted records, updated records
5. Records final job status ("success" or "failed") with details
6. Returns summary dict

**Error Handling:**
- Catches exceptions per config and continues processing other configs
- Records specific error messages in config.test_message for debugging
- Sets test_status to "failed" if any tenant has issues
- Overall job status is "failed" only if all tenants failed

### 2. **Per-Config Ingestion: `_ingest_for_config()`**

```python
async def _ingest_for_config(
    db: Session, 
    config: CostIngestConfig, 
    settings: Settings
) -> dict[str, int]:
```

**Step 1: AWS Role Assumption**
```python
sts = boto3.client("sts", region_name="us-east-1")
role_response = sts.assume_role(
    RoleArn=config.aws_role_arn,
    RoleSessionName=f"finops-cost-ingest-{config.tenant_id}",
    ExternalId=config.aws_external_id or None,
    DurationSeconds=3600,  # 1 hour session
)
credentials = role_response["Credentials"]
s3 = boto3.client(
    "s3",
    aws_access_key_id=credentials["AccessKeyId"],
    aws_secret_access_key=credentials["SecretAccessKey"],
    aws_session_token=credentials["SessionToken"],
)
```

**Step 2: List S3 Objects**
```python
paginator = s3.get_paginator("list_objects_v2")
pages = paginator.paginate(Bucket=config.s3_bucket, Prefix=prefix)

for page in pages:
    for obj in page["Contents"]:
        key = obj["Key"]
        modified = obj["LastModified"]
        
        # Only process new files
        if last_tested and modified <= last_tested:
            continue
        
        # Filter for Parquet files
        if not key.endswith(".parquet") and not key.endswith(".parquet.gz"):
            continue
```

**Step 3: Download & Decompress**
```python
obj_data = s3.get_object(Bucket=config.s3_bucket, Key=key)
body = obj_data["Body"].read()

if key.endswith(".gz"):
    import gzip
    body = gzip.decompress(body)

df = pd.read_parquet(io.BytesIO(body))
```

**Step 4: Upsert to CostDetail**
```python
records = _upsert_cost_details(db, df, config.tenant_id)
```

**Step 5: Update Config Metadata**
```python
config.last_tested_at = utcnow()
config.test_status = "success"
config.test_message = f"Processed {files_processed} files"
db.commit()
```

### 3. **CUR Row Parsing: `_upsert_cost_details()`**

```python
def _upsert_cost_details(
    db: Session, 
    df: pd.DataFrame, 
    tenant_id: str
) -> dict[str, int]:
```

**CUR Column Mapping:**

The function extracts data from AWS CUR Parquet columns:

| CUR Column | Target Field | Notes |
|---|---|---|
| `lineItem/UsageAccountId` | `account_id` | AWS account ID |
| `lineItem/ProductName` | `service` | Service name (EC2, S3, RDS) |
| `pricing/sku` | `sku` | Pricing SKU |
| `lineItem/AvailabilityZone` | `region` | AZ → region (remove trailing letter) |
| `lineItem/UsageStartDate` | `usage_start_date` | YYYY-MM-DD |
| `lineItem/UsageAmount` | `usage_quantity` | Decimal(20,10) |
| `lineItem/UnblendedRate` | `rate` | Decimal(20,10) |
| `lineItem/UnblendedCost` | `cost_before_discount` | Decimal(20,10) |
| `discount/TotalDiscount` | `discount` | Decimal(20,10) |
| `bill/AmortizedCost` | `cost_after_discount` | Decimal(20,10) |
| `resourceTags/*` | `tags` | JSON dict |
| `lineItem/ResourceId` | `resource_id` | AWS resource ID |

**Decimal Precision:**

All cost fields use `Decimal(20, 10)` for **financial accuracy**:
```python
cost_before = Decimal(str(row.get("lineItem/UnblendedCost", 0) or 0))
```

Why not Float?
- Floats have rounding errors in base-2 representation (e.g., 0.1 + 0.2 ≠ 0.3)
- Financial calculations with floats can accumulate errors
- `Decimal` provides exact decimal arithmetic (base-10)

**Duplicate Detection & Upsert:**

1. **Check for existing record** using unique constraint fields:
   ```python
   existing = db.query(CostDetail).filter(
       CostDetail.tenant_id == tenant_id,
       CostDetail.account_id == account_id,
       CostDetail.service == service_name,
       CostDetail.sku == sku,
       CostDetail.region == region,
       CostDetail.usage_start_date == usage_start,
   ).one_or_none()
   ```

2. **If exists**: Update all cost fields (prices may have been adjusted)
   ```python
   existing.cost_before_discount = cost_before
   existing.cost_after_discount = cost_after
   # ... update other fields
   db.add(existing)
   updated_count += 1
   ```

3. **If new**: Insert new record
   ```python
   detail = CostDetail(
       tenant_id=tenant_id,
       account_id=account_id,
       # ... all fields
   )
   db.add(detail)
   inserted_count += 1
   ```

**Error Recovery:**

If batch commit fails with `IntegrityError`, retry row-by-row:
```python
try:
    db.commit()
except IntegrityError:
    db.rollback()
    for _, row in df.iterrows():
        # Insert individual rows
        # Skip if duplicate IntegrityError
```

---

## Dependencies

Add these to `requirements.txt`:

```
boto3>=1.26.0           # AWS SDK for role assumption and S3
pandas>=1.5.0           # DataFrame manipulation
pyarrow>=10.0.0         # Parquet file reading
botocore>=1.29.0        # AWS error handling
```

---

## Configuration

### Environment Setup

1. **Create IAM role in application's AWS account** with permission to assume customer roles:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "sts:AssumeRole",
         "Resource": "arn:aws:iam::*:role/FinOpsServiceRole"
       },
       {
         "Effect": "Allow",
         "Action": "s3:*",
         "Resource": [
           "arn:aws:s3:::*-billing",
           "arn:aws:s3:::*-billing/*"
         ]
       }
     ]
   }
   ```

2. **Create cross-account role in each customer's AWS account**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::my-billing-bucket",
           "arn:aws:s3:::my-billing-bucket/*"
         ]
       }
     ]
   }
   ```
   
   Trust relationship:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "arn:aws:iam::APP_ACCOUNT:role/FinOpsServiceRole"
         },
         "Action": "sts:AssumeRole",
         "Condition": {
           "StringEquals": {
             "sts:ExternalId": "unique-external-id-per-tenant"
           }
         }
       }
     ]
   }
   ```

### schedules.yaml Configuration

```yaml
cost_ingest:
  description: Ingest AWS CUR Parquet files from S3 in 5-minute polling intervals.
  interval: 5m
  batch_size: 100
  retry_on_failure: true
  warm_retention_days: 365
  cold_retention_days: 730
```

---

## API for Admin Setup

This job is managed via database configuration. Future API endpoints (Phase 4) will enable:

```
POST /api/cost/ingest-config
{
  "s3_bucket": "my-billing-bucket",
  "s3_prefix": "AWSLogs/123456789012/costs",
  "aws_role_arn": "arn:aws:iam::123456789012:role/FinOpsServiceRole",
  "aws_external_id": "unique-external-id",
  "enabled": true
}

GET /api/cost/ingest-config
GET /api/cost/ingest-config/{id}
PATCH /api/cost/ingest-config/{id}
PUT /api/cost/ingest-config/{id}/test

GET /api/cost/status
{
  "job_runs": [
    {
      "id": "...",
      "job_name": "cost_ingest",
      "status": "success",
      "started_at": "2026-05-09T10:00:00Z",
      "finished_at": "2026-05-09T10:05:30Z",
      "records_processed": 12450,
      "details": {
        "total_files": 5,
        "configs_processed": 2
      }
    }
  ]
}
```

---

## Monitoring & Debugging

### JobRun Records

Each execution creates a `JobRun` record with:
- **job_name**: "cost_ingest"
- **status**: "running" → "success" or "failed"
- **started_at**: Job start time
- **finished_at**: Job end time
- **records_processed**: Total inserted + updated
- **details**: JSON with file counts, error messages

### Log Messages

The job logs at multiple levels:
- **INFO**: File processing summaries
- **DEBUG**: Skipped files (not newer than last_tested_at)
- **WARNING**: Row-level parsing errors (continues to next row)
- **ERROR**: Config-level errors, AWS API failures

### Common Issues & Resolutions

| Issue | Cause | Resolution |
|---|---|---|
| "No cost ingest configs found" | No CostIngestConfig records in DB | Add config via admin API (Phase 4) |
| "AWS error: AccessDenied" | IAM role lacks S3 permissions | Update cross-account role policy |
| "Failed processing {key}: invalid column" | CUR schema mismatch | Update column mapping for new CUR version |
| "Integrity error during upsert" | Expected for duplicates | Job retries row-by-row and continues |
| "last_tested_at is None" | First run | Job processes all files, sets last_tested_at |

---

## Performance Characteristics

### Throughput
- **Files per run**: Depends on new files in S3 (typically 1-3 per day for normal usage)
- **Rows per file**: 10,000 - 50,000 (daily CUR files)
- **Parse time**: ~2-5 seconds per Parquet file (pandas + arrow)
- **Database time**: ~5-10 seconds for 10k rows (with bulk commit)
- **Total job runtime**: Typically 30-60 seconds per run

### Scaling
- **Multi-tenant**: Each tenant's config processed independently; parallelizable
- **S3 cost**: ~$0.0004 per ListObjects call, ~$0.0004 per GetObject call
- **Database**: Indexes on (tenant_id, account_id, date, service) optimize upserts

### Data Retention
- **Warm storage** (365 days): Query-optimized, fully indexed
- **Cold storage** (730 days): Archive for compliance and year-over-year analysis
- CostDetail records are never deleted (append-only by nature)

---

## Next Steps

**Phase 3: FOCUS Transformation & Normalization**
- Transform CostDetail → FocusCost using ProductCategory and AIServiceClassification mappings
- Run FOCUS transform job every 1 hour (after new CUR data available)
- Populate chargeback_entity and cost_category fields for FinOps allocation

**Phase 4: REST API Endpoints**
- `/api/cost/daily` - Daily cost summaries by service/category
- `/api/cost/summary` - Tenant-wide cost summary
- `/api/focus/export` - Export FocusCost data in FOCUS CSV format
- `/api/ai-services` - AI service costs by model/tier
- `/api/cost/ingest-config` - Admin config management
- `/api/cost/status` - Job run history and status

**Phase 5: React Dashboards**
- Finance Portal: Cost trends, budget vs actual
- FinOps Analytics: Service breakdown, optimization opportunities
- Team Cost Dashboard: Per-team cost allocation
- Executive Summary: High-level burn rate, forecasting

---

## Code Location

- **Job function**: `/Users/pratikagrawal/Documents/Claude/Projects/FinOps/Recommendation-engine/backend/app/jobs.py`
- **Models**: `/Users/pratikagrawal/Documents/Claude/Projects/FinOps/Recommendation-engine/backend/app/models.py`
- **Scheduler config**: `/Users/pratikagrawal/Documents/Claude/Projects/FinOps/Recommendation-engine/config/schedules.yaml`
- **Database**: `/Users/pratikagrawal/Documents/Claude/Projects/FinOps/Recommendation-engine/backend/app/database.py`

---

## Testing Checklist

- [ ] Create test CostIngestConfig with valid S3 credentials
- [ ] Generate test Parquet file with sample CUR data
- [ ] Verify role assumption succeeds
- [ ] Verify S3 list and download work
- [ ] Verify Decimal parsing is accurate (no rounding errors)
- [ ] Verify upsert logic (insert new, update existing)
- [ ] Verify error recovery (bad rows continue processing)
- [ ] Verify JobRun records are created with correct metadata
- [ ] Verify scheduler calls job every 5 minutes
- [ ] Verify multi-tenant isolation (configs don't interfere)
- [ ] Load test with large Parquet files (>100MB)
- [ ] Test graceful degradation if S3 is unavailable
