# Phase 2: Code Changes Reference Guide

**For Code Review & Integration**

---

## Files Modified

### 1. `backend/app/jobs.py`

**Changes**: Added AWS CUR ingestion job with 3 new functions

**Location**: Lines 1-30 (imports), Lines ~165-400 (new functions), Line ~475-485 (scheduler update)

**New Imports**:
```python
import io
import logging
import re
from decimal import Decimal

import boto3
import pandas as pd
from botocore.exceptions import ClientError
from sqlalchemy.exc import IntegrityError

from .models import CostDetail, CostIngestConfig

logger = logging.getLogger(__name__)
```

**Function 1: `run_cost_ingest(settings: Settings) -> dict[str, Any]`**
- Entry point for scheduler
- ~50 lines
- Handles multi-tenant config iteration
- Returns aggregated results

**Function 2: `_ingest_for_config(db, config, settings) -> dict[str, int]`**
- Per-tenant S3 processing
- ~120 lines
- AWS role assumption, S3 listing, file download, Parquet parsing
- Calls _upsert_cost_details for each file
- Returns inserted/updated/files_processed counts

**Function 3: `_upsert_cost_details(db, df, tenant_id) -> dict[str, int]`**
- CUR row parsing and DB upsert
- ~180 lines
- Column mapping, decimal conversion, unique constraint checking
- Batch commit with row-by-row fallback
- Returns inserted/updated counts

**Scheduler Update**: 
```python
# In start_scheduler() around line 475
cost_ingest_interval = interval_minutes(
    schedules.get("cost_ingest", {}).get("interval", "5m")
)
scheduler.add_job(
    run_cost_ingest,
    "interval",
    minutes=cost_ingest_interval,
    args=[settings],
    id="cost_ingest",
    replace_existing=True
)
```

---

### 2. `config/schedules.yaml`

**Changes**: Added cost_ingest job configuration

**Location**: After line 1, before billing_ingest

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

### 3. `backend/requirements.txt`

**Changes**: Added 3 new dependencies

```diff
+ botocore>=1.31       # AWS error handling
+ pandas>=2.0          # DataFrame manipulation
+ pyarrow>=12.0        # Parquet file support
```

---

## Models Used (Not Modified)

These models were created in Phase 1 and are used as-is in Phase 2:

### `CostIngestConfig` (models.py)
```python
class CostIngestConfig(Base):
    __tablename__ = "cost_ingest_configs"
    
    id: str                                    # Primary key
    tenant_id: str                             # Multi-tenant
    s3_bucket: str                             # Billing bucket
    s3_prefix: str                             # CUR path prefix
    aws_role_arn: str                          # Cross-account role
    aws_external_id: str                       # External ID for role
    enabled: bool                              # Enable/disable
    last_tested_at: datetime | None            # Last successful poll
    test_status: str                           # pending/success/failed
    test_message: str                          # Error details
    created_at: datetime                       # Created timestamp
    updated_at: datetime                       # Updated timestamp
```

### `CostDetail` (models.py)
```python
class CostDetail(Base):
    __tablename__ = "cost_details"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "account_id", "service", "sku", 
            "region", "usage_start_date", 
            name="uq_cost_detail"
        ),
    )
    
    # Core identifiers
    id: str
    tenant_id: str                             # Multi-tenant
    account_id: str                            # AWS account
    service: str                               # Service name
    service_code: str                          # Service code
    sku: str                                   # Pricing SKU
    region: str                                # AWS region
    usage_start_date: str                      # YYYY-MM-DD
    usage_end_date: str                        # YYYY-MM-DD
    usage_type: str                            # Usage type
    
    # Financial fields - Decimal(20,10)
    usage_quantity: Decimal
    rate: Decimal
    currency: str
    cost_before_discount: Decimal
    discount: Decimal
    cost_after_discount: Decimal
    cost_with_tax: Decimal
    
    # Metadata
    cost_allocation_tags: dict                 # JSON
    resource_id: str
    tags: dict                                 # JSON
    sourced_from: str                          # "cur" or "focus_export"
    cur_date: str                              # CUR file date
    parsed_at: datetime
```

### `JobRun` (models.py)
```python
class JobRun(Base):
    __tablename__ = "job_runs"
    
    id: str
    tenant_id: str                             # "platform" for cost jobs
    job_name: str                              # "cost_ingest"
    status: str                                # running/success/failed
    started_at: datetime
    finished_at: datetime | None
    records_processed: int
    details: dict                              # JSON with metadata
```

---

## Database Schema (From Phase 1)

No schema changes in Phase 2. All models from Phase 1 are used:

```sql
-- Created in Phase 1, used in Phase 2:

CREATE TABLE cost_ingest_configs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL INDEX,
    s3_bucket VARCHAR(255) NOT NULL,
    s3_prefix VARCHAR(500),
    aws_role_arn VARCHAR(500) NOT NULL,
    aws_external_id VARCHAR(500),
    enabled BOOLEAN DEFAULT TRUE,
    last_tested_at TIMESTAMP WITH TIME ZONE,
    test_status VARCHAR(40),
    test_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE cost_details (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL INDEX,
    account_id VARCHAR(20) NOT NULL INDEX,
    service VARCHAR(100) INDEX,
    service_code VARCHAR(100),
    sku VARCHAR(500) INDEX,
    region VARCHAR(50) INDEX,
    usage_type VARCHAR(500),
    usage_start_date VARCHAR(20) INDEX,
    usage_end_date VARCHAR(20),
    usage_quantity NUMERIC(20,10),
    rate NUMERIC(20,10),
    currency VARCHAR(3),
    cost_before_discount NUMERIC(20,10),
    discount NUMERIC(20,10),
    cost_after_discount NUMERIC(20,10),
    cost_with_tax NUMERIC(20,10),
    cost_allocation_tags JSONB,
    resource_id VARCHAR(500),
    tags JSONB,
    sourced_from VARCHAR(50),
    cur_date VARCHAR(20),
    parsed_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(tenant_id, account_id, service, sku, region, usage_start_date)
);

CREATE TABLE job_runs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) INDEX,
    job_name VARCHAR(120) INDEX,
    status VARCHAR(40),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER,
    details JSONB
);
```

---

## AWS Configuration Requirements

### IAM Role in Application Account

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
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::*-billing",
        "arn:aws:s3:::*-billing/*"
      ]
    }
  ]
}
```

### Cross-Account Role in Customer Account

**Create role**: `FinOpsServiceRole`

**Trust relationship**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::APP_ACCOUNT_ID:role/FinOpsServiceRole"
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

**Inline policy**:
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

---

## Testing & Validation

### Manual Test Flow

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Start database (PostgreSQL recommended for production)
# Already configured in settings.py

# 3. Create test config
python -c "
from app.database import SessionLocal
from app.models import CostIngestConfig, new_id

db = SessionLocal()
config = CostIngestConfig(
    id=new_id(),
    tenant_id='test-tenant',
    s3_bucket='my-billing-bucket',
    s3_prefix='AWSLogs/123456789012/costs',
    aws_role_arn='arn:aws:iam::123456789012:role/FinOpsServiceRole',
    aws_external_id='test-external-id',
    enabled=True
)
db.add(config)
db.commit()
print(f'Created config: {config.id}')
"

# 4. Trigger job (testing in dev environment)
python -c "
import asyncio
from app.settings import get_settings
from app.jobs import run_cost_ingest

settings = get_settings()
result = asyncio.run(run_cost_ingest(settings))
print(f'Job result: {result}')
"

# 5. Verify data
python -c "
from app.database import SessionLocal
from app.models import CostDetail, JobRun

db = SessionLocal()
records = db.query(CostDetail).filter(
    CostDetail.tenant_id == 'test-tenant'
).count()
print(f'Total records: {records}')

runs = db.query(JobRun).filter(
    JobRun.job_name == 'cost_ingest'
).order_by(JobRun.started_at.desc()).first()
if runs:
    print(f'Last job: {runs.status}, {runs.records_processed} records')
"
```

### Unit Test Template

```python
# tests/test_cost_ingest.py

import pytest
from decimal import Decimal
from app.jobs import _upsert_cost_details
from app.models import CostDetail
from app.database import SessionLocal
import pandas as pd

def test_decimal_precision():
    """Verify cost fields maintain decimal precision"""
    df = pd.DataFrame({
        'lineItem/UsageAccountId': ['123456789012'],
        'lineItem/ProductName': ['EC2'],
        'pricing/sku': ['ABC123'],
        'lineItem/AvailabilityZone': ['us-east-1a'],
        'lineItem/UsageStartDate': ['2026-05-09'],
        'lineItem/UnblendedCost': ['0.123456789'],  # High precision
    })
    
    db = SessionLocal()
    result = _upsert_cost_details(db, df, 'test-tenant')
    
    assert result['inserted'] == 1
    record = db.query(CostDetail).first()
    assert record.cost_before_discount == Decimal('0.123456789')

def test_idempotent_upsert():
    """Verify duplicate handling works correctly"""
    df = pd.DataFrame({
        'lineItem/UsageAccountId': ['123456789012'],
        'lineItem/ProductName': ['EC2'],
        'pricing/sku': ['ABC123'],
        'lineItem/AvailabilityZone': ['us-east-1a'],
        'lineItem/UsageStartDate': ['2026-05-09'],
        'lineItem/UnblendedCost': ['100.00'],
    })
    
    db = SessionLocal()
    
    # First insert
    result1 = _upsert_cost_details(db, df, 'test-tenant')
    assert result1['inserted'] == 1
    
    # Second insert (duplicate)
    result2 = _upsert_cost_details(db, df, 'test-tenant')
    assert result2['updated'] == 1
    assert result2['inserted'] == 0
    
    # Verify single record
    count = db.query(CostDetail).count()
    assert count == 1
```

---

## Integration Checklist

- [ ] Pull latest code from repository
- [ ] Install new dependencies: `pip install -r backend/requirements.txt`
- [ ] Run database migrations (if any pending from Phase 1)
- [ ] Create test CostIngestConfig with valid AWS credentials
- [ ] Verify scheduler starts without errors
- [ ] Check first job run (should appear in JobRun table within 5 minutes)
- [ ] Verify CostDetail records appear with correct tenant_id
- [ ] Check logs for any ERROR or WARNING messages
- [ ] Run unit tests (if test suite available)
- [ ] Validate decimal precision in cost fields
- [ ] Test multi-tenant isolation (separate configs, separate data)
- [ ] Stress test with large Parquet files (>100MB)

---

## Rollback Plan (If Needed)

If Phase 2 needs to be reverted:

```bash
# 1. Revert jobs.py to Phase 1 version
git checkout HEAD~1 backend/app/jobs.py

# 2. Revert schedules.yaml
git checkout HEAD~1 config/schedules.yaml

# 3. Revert requirements.txt
git checkout HEAD~1 backend/requirements.txt

# 4. Restart scheduler
# The cost_ingest job won't be registered

# 5. Clean up database (optional)
DELETE FROM job_runs WHERE job_name = 'cost_ingest';
```

---

## Performance Benchmarks (Expected)

| Metric | Expected Value |
|---|---|
| S3 List API latency | 1-2 seconds |
| Parquet parse (10k rows) | 2-5 seconds |
| Database insert (10k rows) | 5-10 seconds |
| Total job runtime | 30-60 seconds |
| Records per day | 50k - 200k (depends on usage) |
| Storage per month | 10-50 GB (depends on usage) |

---

## Monitoring SQL Queries

```sql
-- Check job execution history
SELECT 
    id, job_name, status, started_at, finished_at,
    (finished_at - started_at) as duration,
    records_processed
FROM job_runs 
WHERE job_name = 'cost_ingest'
ORDER BY started_at DESC
LIMIT 20;

-- Failed jobs only
SELECT 
    id, started_at, status,
    details->>'error' as error
FROM job_runs 
WHERE job_name = 'cost_ingest' AND status = 'failed'
ORDER BY started_at DESC;

-- Records ingested by tenant
SELECT 
    tenant_id, COUNT(*) as record_count,
    MIN(usage_start_date) as earliest_date,
    MAX(usage_start_date) as latest_date,
    SUM(cost_after_discount::numeric) as total_cost
FROM cost_details
GROUP BY tenant_id;

-- Ingest config status
SELECT 
    tenant_id, enabled, test_status, last_tested_at,
    test_message
FROM cost_ingest_configs
ORDER BY last_tested_at DESC;
```

---

**Phase 2 Implementation Complete ✅**
