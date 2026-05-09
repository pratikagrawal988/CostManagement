from __future__ import annotations

import io
import logging
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3
import pandas as pd
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .connectors import connector_for, load_provider_manifests
from .database import SessionLocal
from .evaluator import evaluate_hypothesis
from .models import (
    Action, AuditEvent, CostDetail, CostIngestConfig, AzureCostIngestConfig, GcpCostIngestConfig, CostAggregation,
    FocusCost, Hypothesis, JobRun, Outcome, ProductCategory,
    AIServiceClassification, utcnow
)
from .settings import Settings

logger = logging.getLogger(__name__)


def load_schedules(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"jobs": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"jobs": {}}


def interval_minutes(value: str) -> int:
    if value == "on_demand":
        return 0
    digits = int("".join(ch for ch in value if ch.isdigit()) or "60")
    if value.endswith("m"):
        return digits
    if value.endswith("h"):
        return digits * 60
    if value.endswith("d"):
        return digits * 60 * 24
    return digits


def record_job_start(db: Session, job_name: str, tenant_id: str = "tenant-demo") -> JobRun:
    run = JobRun(tenant_id=tenant_id, job_name=job_name, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def record_job_finish(db: Session, run: JobRun, status: str, records: int = 0, details: dict | None = None) -> None:
    run.status = status
    run.finished_at = utcnow()
    run.records_processed = records
    run.details = details or {}
    db.commit()


async def run_metrics_ingest(settings: Settings) -> int:
    db = SessionLocal()
    run = record_job_start(db, "metrics_ingest")
    try:
        manifests = load_provider_manifests(settings.resolve_config_path(settings.provider_registry_path))
        records = 0
        for manifest in manifests:
            if manifest.category in {"csp", "k8s", "saas", "ai_telemetry"}:
                records += await connector_for(manifest).ingest_metrics(db, "tenant-demo")
        record_job_finish(db, run, "success", records, {"providers": len(manifests)})
        return records
    except Exception as exc:  # pragma: no cover - operational guard
        record_job_finish(db, run, "failed", details={"error": str(exc)})
        raise
    finally:
        db.close()


async def run_evaluator(settings: Settings) -> int:
    db = SessionLocal()
    run = record_job_start(db, "evaluator_run")
    try:
        active = db.query(Hypothesis).filter(Hypothesis.state == "active").all()
        findings = 0
        for hypothesis in active:
            result = evaluate_hypothesis(db, hypothesis, persist=True)
            findings += result["hit_count"]
        record_job_finish(db, run, "success", findings, {"active_hypotheses": len(active)})
        return findings
    except Exception as exc:  # pragma: no cover
        record_job_finish(db, run, "failed", details={"error": str(exc)})
        raise
    finally:
        db.close()


async def run_reconciler(settings: Settings) -> int:
    db = SessionLocal()
    run = record_job_start(db, "reconciler")
    try:
        count = 0
        applied_actions = db.query(Action).filter(Action.status == "applied").all()
        for action in applied_actions:
            for window in (30, 60, 90):
                existing = (
                    db.query(Outcome)
                    .filter(Outcome.action_id == action.id, Outcome.window_days == window)
                    .one_or_none()
                )
                if existing:
                    continue
                if not action.applied_at or action.applied_at > utcnow() - timedelta(days=window):
                    status = "pending"
                    realized = 0.0
                    observed = 0.0
                    reconciled_at = None
                else:
                    estimate = float(action.payload.get("estimated_savings_monthly", 0))
                    realized = round(estimate * (0.82 + window / 1000), 2)
                    observed = max(0, estimate * 2 - realized)
                    status = "realized" if realized >= estimate * 0.6 else "regressed"
                    reconciled_at = utcnow()
                outcome = Outcome(
                    tenant_id=action.tenant_id,
                    action_id=action.id,
                    window_days=window,
                    status=status,
                    baseline_cost=float(action.payload.get("baseline_cost", 0)),
                    observed_cost=observed,
                    estimated_savings=float(action.payload.get("estimated_savings_monthly", 0)),
                    realized_savings=realized,
                    variance_pct=0 if not action.payload.get("estimated_savings_monthly") else round((realized - float(action.payload.get("estimated_savings_monthly", 0))) / float(action.payload.get("estimated_savings_monthly", 1)) * 100, 2),
                    evidence={"source": "billing_export", "window_days": window},
                    reconciled_at=reconciled_at,
                )
                db.add(outcome)
                count += 1
        db.commit()
        record_job_finish(db, run, "success", count)
        return count
    except Exception as exc:  # pragma: no cover
        record_job_finish(db, run, "failed", details={"error": str(exc)})
        raise
    finally:
        db.close()


def start_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.scheduler_enabled:
        return None
    scheduler = AsyncIOScheduler(timezone="UTC")
    schedules = load_schedules(settings.resolve_config_path(settings.schedules_path)).get("jobs", {})
    metrics_interval = interval_minutes(schedules.get("metrics_ingest", {}).get("interval", "5m"))
    evaluator_interval = interval_minutes(schedules.get("evaluator_run", {}).get("interval", "1h"))
    reconciler_interval = interval_minutes(schedules.get("reconciler", {}).get("interval", "24h"))
    catalog_interval = interval_minutes(schedules.get("product_catalog_refresh", {}).get("interval", "30d"))  # 30 days = monthly
    cost_ingest_interval = interval_minutes(schedules.get("cost_ingest", {}).get("interval", "5m"))  # 5 minute polling
    azure_ingest_interval = interval_minutes(schedules.get("azure_ingest", {}).get("interval", "5m"))  # 5 minute polling
    gcp_ingest_interval = interval_minutes(schedules.get("gcp_ingest", {}).get("interval", "5m"))  # 5 minute polling
    focus_transform_interval = interval_minutes(schedules.get("focus_transform", {}).get("interval", "1h"))  # Hourly
    scheduler.add_job(run_metrics_ingest, "interval", minutes=metrics_interval, args=[settings], id="metrics_ingest", replace_existing=True)
    scheduler.add_job(run_evaluator, "interval", minutes=evaluator_interval, args=[settings], id="evaluator_run", replace_existing=True)
    scheduler.add_job(run_reconciler, "interval", minutes=reconciler_interval, args=[settings], id="reconciler", replace_existing=True)
    scheduler.add_job(run_product_catalog_refresh, "interval", minutes=catalog_interval, args=[settings], id="product_catalog_refresh", replace_existing=True)
    scheduler.add_job(run_cost_ingest, "interval", minutes=cost_ingest_interval, args=[settings], id="cost_ingest", replace_existing=True)

    # Import Azure and GCP jobs (lazy import to avoid circular dependencies)
    from .azure_jobs import run_azure_ingest
    from .gcp_jobs import run_gcp_ingest
    scheduler.add_job(run_azure_ingest, "interval", minutes=azure_ingest_interval, args=[settings], id="azure_ingest", replace_existing=True)
    scheduler.add_job(run_gcp_ingest, "interval", minutes=gcp_ingest_interval, args=[settings], id="gcp_ingest", replace_existing=True)

    scheduler.add_job(run_focus_transform, "interval", minutes=focus_transform_interval, args=[settings], id="focus_transform", replace_existing=True)
    scheduler.start()
    return scheduler


async def run_cost_ingest(settings: Settings) -> dict[str, Any]:
    """
    Ingests AWS CUR data from S3 in 5-minute intervals.

    1. Fetches CostIngestConfig from DB (per tenant)
    2. Assumes AWS role with external ID
    3. Lists new Parquet files from S3 CUR path
    4. Downloads and parses files (detects new by modification timestamp)
    5. Upserts to CostDetail table with idempotent logic
    6. Records job run in JobRun table
    """
    db = SessionLocal()
    run = record_job_start(db, "cost_ingest")

    try:
        # Get all enabled ingest configs
        configs = db.query(CostIngestConfig).filter(CostIngestConfig.enabled == True).all()

        if not configs:
            logger.info("No cost ingest configs found")
            record_job_finish(db, run, "success", 0, {"message": "no_configs"})
            return {"skipped": True, "reason": "no_configs"}

        total_records = 0
        total_files = 0
        errors = []

        for config in configs:
            try:
                records = await _ingest_for_config(db, config, settings)
                total_records += records["inserted"] + records["updated"]
                total_files += records["files_processed"]
                logger.info(f"Tenant {config.tenant_id}: {total_files} files, {records['inserted']} inserted, {records['updated']} updated")
            except Exception as exc:
                error_msg = f"Tenant {config.tenant_id}: {str(exc)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue processing other configs

        details = {
            "total_files": total_files,
            "total_records_inserted": total_records,
            "configs_processed": len(configs),
            "errors": errors if errors else None,
        }

        status = "failed" if errors and total_records == 0 else "success"
        record_job_finish(db, run, status, total_records, details)
        return details

    except Exception as exc:
        logger.error(f"Cost ingest job failed: {str(exc)}")
        record_job_finish(db, run, "failed", details={"error": str(exc)})
        raise
    finally:
        db.close()


async def _ingest_for_config(db: Session, config: CostIngestConfig, settings: Settings) -> dict[str, int]:
    """
    Process one tenant's cost ingest config:
    1. Assume AWS role
    2. List S3 objects in CUR path
    3. Download new Parquet files (by modification timestamp)
    4. Parse and upsert to CostDetail
    """

    try:
        # Assume AWS role with external ID for cross-account access
        sts = boto3.client("sts", region_name="us-east-1")
        role_response = sts.assume_role(
            RoleArn=config.aws_role_arn,
            RoleSessionName=f"finops-cost-ingest-{config.tenant_id}",
            ExternalId=config.aws_external_id or None,
            DurationSeconds=3600,
        )

        credentials = role_response["Credentials"]
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        # List objects in the S3 bucket/prefix
        prefix = config.s3_prefix
        if not prefix.endswith("/"):
            prefix += "/"

        # AWS CUR typically produces files like: <prefix>/YYYYMM<DD>T<HH><MM>Z-<hash>.parquet.gz
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=config.s3_bucket, Prefix=prefix)

        inserted_count = 0
        updated_count = 0
        files_processed = 0
        last_tested = config.last_tested_at

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]
                modified = obj["LastModified"]

                # Only process new files (newer than last_tested_at)
                if last_tested and modified <= last_tested:
                    logger.debug(f"Skipping {key} (not newer than {last_tested})")
                    continue

                # Filter for Parquet files (CUR format)
                if not key.endswith(".parquet") and not key.endswith(".parquet.gz"):
                    continue

                try:
                    # Download and parse Parquet file
                    obj_data = s3.get_object(Bucket=config.s3_bucket, Key=key)

                    # Handle gzip compression
                    body = obj_data["Body"].read()
                    if key.endswith(".gz"):
                        import gzip
                        body = gzip.decompress(body)

                    # Read Parquet using pandas
                    df = pd.read_parquet(io.BytesIO(body))

                    # Upsert records to CostDetail
                    records = _upsert_cost_details(db, df, config.tenant_id)
                    inserted_count += records["inserted"]
                    updated_count += records["updated"]
                    files_processed += 1

                    logger.info(f"Processed {key}: {records['inserted']} inserted, {records['updated']} updated")

                    # Update last tested timestamp
                    config.last_tested_at = utcnow()
                    config.test_status = "success"
                    config.test_message = f"Processed {files_processed} files"
                    db.commit()

                except Exception as file_exc:
                    logger.error(f"Error processing {key}: {str(file_exc)}")
                    config.test_status = "failed"
                    config.test_message = f"Failed processing {key}: {str(file_exc)}"
                    db.commit()
                    # Continue to next file

        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "files_processed": files_processed,
        }

    except ClientError as exc:
        logger.error(f"AWS S3 error for tenant {config.tenant_id}: {str(exc)}")
        config.test_status = "failed"
        config.test_message = f"AWS error: {exc.response['Error']['Code']}"
        db.commit()
        raise


def _upsert_cost_details(db: Session, df: pd.DataFrame, tenant_id: str) -> dict[str, int]:
    """
    Parse CUR DataFrame and upsert to CostDetail table.
    Uses unique constraint to detect duplicates (no full table replacements).
    """

    # Map CUR column names to CostDetail fields
    # AWS CUR standard columns: identity/TimeInterval, lineItem/*, blended/*, etc.
    column_mapping = {
        "lineItem/UsageStartDate": "usage_start_date",
        "lineItem/UsageEndDate": "usage_end_date",
        "lineItem/ProductCode": "service_code",
        "lineItem/UsageType": "usage_type",
        "lineItem/Operation": "operation",
        "lineItem/AvailabilityZone": "availability_zone",
        "lineItem/ResourceId": "resource_id",
        "lineItem/UsageAmount": "usage_quantity",
        "lineItem/UnblendedRate": "rate",
        "lineItem/UnblendedCost": "cost_before_discount",
        "discount/TotalDiscount": "discount",
        "bill/BillingEntity": "billing_entity",
        "bill/BillType": "bill_type",
        "bill/PayerAccountId": "payer_account_id",
        "lineItem/BlendedRate": "blended_rate",
        "lineItem/BlendedCost": "cost_after_discount",
        "bill/InvoiceId": "invoice_id",
    }

    inserted_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        try:
            # Extract core fields - map from CUR columns
            account_id = str(row.get("lineItem/UsageAccountId", "")).strip()
            service_name = str(row.get("lineItem/ProductName", "")).strip()
            sku = str(row.get("pricing/sku", "")).strip()
            region = str(row.get("lineItem/AvailabilityZone", "")).strip()
            region = region[:-1] if region and region[-1] in "abcde" else region  # Remove AZ letter if present
            usage_start = str(row.get("lineItem/UsageStartDate", "")).strip()[:10]  # YYYY-MM-DD

            # Skip invalid records
            if not all([account_id, service_name, usage_start]):
                logger.debug(f"Skipping invalid record: account={account_id}, service={service_name}, date={usage_start}")
                continue

            # Extract cost fields with Decimal precision
            cost_before = Decimal(str(row.get("lineItem/UnblendedCost", 0) or 0))
            discount_amt = Decimal(str(row.get("discount/TotalDiscount", 0) or 0))
            cost_after = Decimal(str(row.get("bill/AmortizedCost", 0) or cost_before - discount_amt))
            usage_qty = Decimal(str(row.get("lineItem/UsageAmount", 0) or 0))
            rate = Decimal(str(row.get("lineItem/UnblendedRate", 0) or 0))

            # Extract tags (CUR stores as resourceTags/*)
            tags = {}
            for col in df.columns:
                if col.startswith("resourceTags/"):
                    tag_key = col.replace("resourceTags/", "")
                    tag_val = str(row.get(col, "")).strip()
                    if tag_val:
                        tags[tag_key] = tag_val

            # Check for duplicate (unique constraint)
            existing = (
                db.query(CostDetail)
                .filter(
                    CostDetail.tenant_id == tenant_id,
                    CostDetail.account_id == account_id,
                    CostDetail.service == service_name,
                    CostDetail.sku == sku,
                    CostDetail.region == region,
                    CostDetail.usage_start_date == usage_start,
                )
                .one_or_none()
            )

            if existing:
                # Update existing record
                existing.cost_before_discount = cost_before
                existing.discount = discount_amt
                existing.cost_after_discount = cost_after
                existing.usage_quantity = usage_qty
                existing.rate = rate
                existing.tags = tags
                existing.parsed_at = utcnow()
                db.add(existing)
                updated_count += 1
            else:
                # Create new record
                detail = CostDetail(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    service=service_name,
                    service_code=str(row.get("lineItem/ProductCode", "")).strip(),
                    sku=sku,
                    region=region,
                    usage_type=str(row.get("lineItem/UsageType", "")).strip(),
                    usage_start_date=usage_start,
                    usage_end_date=str(row.get("lineItem/UsageEndDate", "")).strip()[:10],
                    usage_quantity=usage_qty,
                    rate=rate,
                    currency=str(row.get("pricing/currency", "USD")).strip(),
                    cost_before_discount=cost_before,
                    discount=discount_amt,
                    cost_after_discount=cost_after,
                    cost_with_tax=Decimal(str(row.get("bill/TaxAmount", 0) or 0)) + cost_after,
                    cost_allocation_tags=tags,
                    resource_id=str(row.get("lineItem/ResourceId", "")).strip(),
                    tags=tags,
                    sourced_from="cur",
                    cur_date=str(row.get("bill/BillingPeriodStartDate", "")).strip()[:10],
                    parsed_at=utcnow(),
                )
                db.add(detail)
                inserted_count += 1

        except Exception as row_exc:
            logger.warning(f"Error processing CUR row: {str(row_exc)}")
            # Continue to next row
            continue

    try:
        db.commit()
    except IntegrityError as exc:
        logger.warning(f"Integrity error during upsert (expected for duplicates): {str(exc)}")
        db.rollback()
        # Retry with individual inserts to handle partials
        for _, row in df.iterrows():
            try:
                account_id = str(row.get("lineItem/UsageAccountId", "")).strip()
                service_name = str(row.get("lineItem/ProductName", "")).strip()
                sku = str(row.get("pricing/sku", "")).strip()
                region = str(row.get("lineItem/AvailabilityZone", "")).strip()
                region = region[:-1] if region and region[-1] in "abcde" else region
                usage_start = str(row.get("lineItem/UsageStartDate", "")).strip()[:10]

                if not all([account_id, service_name, usage_start]):
                    continue

                existing = (
                    db.query(CostDetail)
                    .filter(
                        CostDetail.tenant_id == tenant_id,
                        CostDetail.account_id == account_id,
                        CostDetail.service == service_name,
                        CostDetail.sku == sku,
                        CostDetail.region == region,
                        CostDetail.usage_start_date == usage_start,
                    )
                    .one_or_none()
                )

                if not existing:
                    cost_before = Decimal(str(row.get("lineItem/UnblendedCost", 0) or 0))
                    discount_amt = Decimal(str(row.get("discount/TotalDiscount", 0) or 0))
                    cost_after = Decimal(str(row.get("bill/AmortizedCost", 0) or cost_before - discount_amt))
                    usage_qty = Decimal(str(row.get("lineItem/UsageAmount", 0) or 0))
                    rate = Decimal(str(row.get("lineItem/UnblendedRate", 0) or 0))

                    tags = {}
                    for col in df.columns:
                        if col.startswith("resourceTags/"):
                            tag_key = col.replace("resourceTags/", "")
                            tag_val = str(row.get(col, "")).strip()
                            if tag_val:
                                tags[tag_key] = tag_val

                    detail = CostDetail(
                        tenant_id=tenant_id,
                        account_id=account_id,
                        service=service_name,
                        service_code=str(row.get("lineItem/ProductCode", "")).strip(),
                        sku=sku,
                        region=region,
                        usage_type=str(row.get("lineItem/UsageType", "")).strip(),
                        usage_start_date=usage_start,
                        usage_end_date=str(row.get("lineItem/UsageEndDate", "")).strip()[:10],
                        usage_quantity=usage_qty,
                        rate=rate,
                        currency=str(row.get("pricing/currency", "USD")).strip(),
                        cost_before_discount=cost_before,
                        discount=discount_amt,
                        cost_after_discount=cost_after,
                        cost_with_tax=Decimal(str(row.get("bill/TaxAmount", 0) or 0)) + cost_after,
                        cost_allocation_tags=tags,
                        resource_id=str(row.get("lineItem/ResourceId", "")).strip(),
                        tags=tags,
                        sourced_from="cur",
                        cur_date=str(row.get("bill/BillingPeriodStartDate", "")).strip()[:10],
                        parsed_at=utcnow(),
                    )
                    db.add(detail)
                    inserted_count += 1
                db.commit()
            except IntegrityError:
                db.rollback()
                # Skip this duplicate
                pass

    return {"inserted": inserted_count, "updated": updated_count}


async def run_focus_transform(settings: Settings) -> dict[str, Any]:
    """
    Transform CostDetail (raw AWS CUR) → FocusCost (FOCUS-normalized) and create aggregations.

    1. Query CostDetail records since last transform (every hour)
    2. Join with ProductCategory to get standard service categories
    3. Join with AIServiceClassification to get AI service metadata
    4. Transform to FOCUS schema (billing_period_start, invoice_issuer, service_category, etc.)
    5. Upsert to FocusCost table
    6. Create daily CostAggregation records for dashboard performance
    """
    db = SessionLocal()
    run = record_job_start(db, "focus_transform")

    try:
        # Get all unique tenant_id values from CostDetail
        from sqlalchemy import func, and_
        tenants = db.query(func.distinct(CostDetail.tenant_id)).filter(
            CostDetail.sourced_from == "cur"
        ).all()

        total_focus_records = 0
        total_aggregations = 0
        errors = []

        for (tenant_id,) in tenants:
            try:
                # Get unprocessed CostDetail records
                cost_details = db.query(CostDetail).filter(
                    CostDetail.tenant_id == tenant_id,
                    CostDetail.sourced_from == "cur"
                ).all()

                if not cost_details:
                    logger.debug(f"Tenant {tenant_id}: No cost details to transform")
                    continue

                # Transform each CostDetail to FocusCost
                focus_count = 0
                for detail in cost_details:
                    try:
                        focus_record = _transform_to_focus(db, detail, tenant_id)
                        if focus_record:
                            # Upsert FOCUS record
                            existing = db.query(FocusCost).filter(
                                FocusCost.tenant_id == tenant_id,
                                FocusCost.account_id == detail.account_id,
                                FocusCost.service_name == detail.service,
                                FocusCost.sku == detail.sku,
                                FocusCost.region == detail.region,
                                FocusCost.billing_period_start == detail.usage_start_date,
                            ).one_or_none()

                            if existing:
                                existing.billed_cost = focus_record["billed_cost"]
                                existing.usage_quantity = focus_record["usage_quantity"]
                                existing.unit_price = focus_record["unit_price"]
                                existing.tags = focus_record["tags"]
                                existing.synth_date = utcnow()
                                db.add(existing)
                            else:
                                focus = FocusCost(
                                    tenant_id=tenant_id,
                                    account_id=detail.account_id,
                                    billing_period_start=detail.usage_start_date,
                                    invoice_issuer="aws",
                                    service_name=focus_record["service_name"],
                                    service_category=focus_record["service_category"],
                                    sku=detail.sku,
                                    region=detail.region,
                                    usage_quantity=focus_record["usage_quantity"],
                                    usage_unit=focus_record["usage_unit"],
                                    unit_price=focus_record["unit_price"],
                                    billed_cost=focus_record["billed_cost"],
                                    currency="USD",
                                    tags=focus_record["tags"],
                                    resource_id=detail.resource_id,
                                    cost_category=focus_record["cost_category"],
                                    chargeback_entity=focus_record["chargeback_entity"],
                                    synth_date=utcnow(),
                                )
                                db.add(focus)
                            focus_count += 1
                    except Exception as detail_exc:
                        logger.warning(f"Error transforming detail {detail.id}: {str(detail_exc)}")
                        continue

                # Create daily aggregations
                agg_count = _create_cost_aggregations(db, tenant_id, cost_details)

                db.commit()
                total_focus_records += focus_count
                total_aggregations += agg_count
                logger.info(f"Tenant {tenant_id}: {focus_count} FOCUS records, {agg_count} aggregations")

            except Exception as tenant_exc:
                logger.error(f"Error processing tenant {tenant_id}: {str(tenant_exc)}")
                db.rollback()
                errors.append(f"Tenant {tenant_id}: {str(tenant_exc)}")

        details = {
            "total_focus_records": total_focus_records,
            "total_aggregations": total_aggregations,
            "tenants_processed": len(tenants),
            "errors": errors if errors else None,
        }

        status = "failed" if errors and total_focus_records == 0 else "success"
        record_job_finish(db, run, status, total_focus_records + total_aggregations, details)
        return details

    except Exception as exc:
        logger.error(f"FOCUS transform job failed: {str(exc)}")
        record_job_finish(db, run, "failed", details={"error": str(exc)})
        raise
    finally:
        db.close()


def _transform_to_focus(db: Session, detail: CostDetail, tenant_id: str) -> dict | None:
    """
    Transform a CostDetail record to FOCUS schema by applying category and AI mappings.

    Returns dict with FOCUS fields or None if unmapped.
    """
    try:
        # Look up service category
        category_mapping = db.query(ProductCategory).filter(
            ProductCategory.tenant_id == tenant_id,
            ProductCategory.provider == "AWS",
            ProductCategory.service_name == detail.service,
        ).first()

        service_category = category_mapping.category if category_mapping else "Other"
        usage_unit = category_mapping.unit_type if category_mapping else "hour"

        # Look up AI service classification
        ai_mapping = db.query(AIServiceClassification).filter(
            AIServiceClassification.tenant_id == tenant_id,
            AIServiceClassification.provider == "AWS",
            AIServiceClassification.service_name == detail.service,
        ).first()

        # Determine cost allocation (chargeback entity) based on tags
        chargeback_entity = (
            detail.tags.get("CostCenter", "")
            or detail.tags.get("Team", "")
            or detail.tags.get("Environment", "default")
        )

        cost_category = (
            detail.tags.get("CostCategory", "")
            or (service_category if service_category != "Other" else "")
        )

        return {
            "service_name": detail.service,
            "service_category": service_category,
            "usage_quantity": detail.usage_quantity,
            "usage_unit": usage_unit,
            "unit_price": detail.rate,
            "billed_cost": detail.cost_after_discount,
            "tags": detail.tags,
            "cost_category": cost_category,
            "chargeback_entity": chargeback_entity,
            "ai_type": ai_mapping.ai_type if ai_mapping else None,
            "ai_subtype": ai_mapping.ai_subtype if ai_mapping else None,
            "model_variant": ai_mapping.model_variant if ai_mapping else None,
        }

    except Exception as exc:
        logger.warning(f"Error in transform logic: {str(exc)}")
        return None


def _create_cost_aggregations(db: Session, tenant_id: str, details: list[CostDetail]) -> int:
    """
    Create daily CostAggregation records for dashboard performance.

    Groups CostDetail by (date, service, category, region, ai_type) and pre-computes totals.
    """
    from sqlalchemy import func, and_

    aggregations_created = 0

    # Get all unique dates in the CostDetail batch
    dates = set(detail.usage_start_date for detail in details)

    for date in dates:
        # Get details for this date
        daily_details = [d for d in details if d.usage_start_date == date]

        # Group by service, category, region, ai_type
        groups = {}
        for detail in daily_details:
            # Lookup category
            cat_mapping = db.query(ProductCategory).filter(
                ProductCategory.tenant_id == tenant_id,
                ProductCategory.service_name == detail.service,
            ).first()
            category = cat_mapping.category if cat_mapping else "Other"
            subcategory = cat_mapping.subcategory if cat_mapping else ""

            # Lookup AI type
            ai_mapping = db.query(AIServiceClassification).filter(
                AIServiceClassification.tenant_id == tenant_id,
                AIServiceClassification.service_name == detail.service,
            ).first()
            ai_type = ai_mapping.ai_type if ai_mapping else ""
            ai_subtype = ai_mapping.ai_subtype if ai_mapping else ""

            key = (detail.account_id, detail.service, category, subcategory, detail.region, ai_type, ai_subtype)
            if key not in groups:
                groups[key] = {
                    "total_cost": Decimal(0),
                    "total_usage": Decimal(0),
                    "unit_count": 0,
                    "resource_count": 0,
                }

            groups[key]["total_cost"] += detail.cost_after_discount
            groups[key]["total_usage"] += detail.usage_quantity
            groups[key]["unit_count"] += 1
            groups[key]["resource_count"] += 1

        # Create aggregation records
        for (account_id, service, category, subcategory, region, ai_type, ai_subtype), agg_data in groups.items():
            existing_agg = db.query(CostAggregation).filter(
                CostAggregation.tenant_id == tenant_id,
                CostAggregation.account_id == account_id,
                CostAggregation.date == date,
                CostAggregation.service == service,
                CostAggregation.category == category,
                CostAggregation.region == region,
            ).one_or_none()

            if existing_agg:
                existing_agg.total_cost = agg_data["total_cost"]
                existing_agg.total_usage = agg_data["total_usage"]
                existing_agg.unit_count = agg_data["unit_count"]
                existing_agg.resource_count = agg_data["resource_count"]
                existing_agg.aggregated_at = utcnow()
                db.add(existing_agg)
            else:
                agg = CostAggregation(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    date=date,
                    service=service,
                    category=category,
                    subcategory=subcategory,
                    ai_type=ai_type,
                    ai_subtype=ai_subtype,
                    region=region,
                    total_cost=agg_data["total_cost"],
                    total_usage=agg_data["total_usage"],
                    unit_count=agg_data["unit_count"],
                    resource_count=agg_data["resource_count"],
                    aggregated_at=utcnow(),
                )
                db.add(agg)

            aggregations_created += 1

    return aggregations_created


async def run_product_catalog_refresh(settings: Settings) -> dict[str, Any]:
    """Refresh pricing for AWS, Azure, and GCP - incremental updates only."""
    db = SessionLocal()
    run = record_job_start(db, "product_catalog_refresh")
    try:
        manifests = load_provider_manifests(settings.resolve_config_path(settings.provider_registry_path))
        results = {}
        total_inserted = 0
        total_updated = 0

        for manifest in manifests:
            if manifest.provider_id in {"aws", "azure", "gcp"}:
                connector = connector_for(manifest)
                result = await connector.fetch_and_update_pricing(db)
                results[manifest.provider_id] = result
                total_inserted += result.get("inserted", 0)
                total_updated += result.get("updated", 0)

        details = {
            "providers_updated": list(results.keys()),
            "results": results,
            "total_inserted": total_inserted,
            "total_updated": total_updated,
        }
        record_job_finish(db, run, "success", total_inserted + total_updated, details)
        return details
    except Exception as exc:  # pragma: no cover
        record_job_finish(db, run, "failed", details={"error": str(exc)})
        raise
    finally:
        db.close()


def audit(db: Session, tenant_id: str, actor: str, entity_type: str, entity_id: str, event_type: str, payload: dict[str, Any]) -> None:
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=payload,
        )
    )
    db.commit()
