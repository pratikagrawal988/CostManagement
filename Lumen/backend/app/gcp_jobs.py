"""
GCP (Google Cloud Platform) BigQuery Cost Ingestion

Handles integration with GCP Cloud Billing and BigQuery:
1. Authenticates with Service Account credentials
2. Retrieves cost data from BigQuery (gcp_billing_export_v1)
3. Parses and normalizes GCP cost data
4. Upserts to CostDetail table for FOCUS transformation
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from google.cloud import bigquery
from google.oauth2 import service_account
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import (
    GcpCostIngestConfig, CostDetail, CostAggregation,
    FocusCost, JobRun, ProductCategory, utcnow
)
from .settings import Settings

logger = logging.getLogger(__name__)


def get_bigquery_client(config: GcpCostIngestConfig) -> bigquery.Client:
    """
    Create BigQuery client using Service Account credentials.

    Args:
        config: GcpCostIngestConfig with service account key

    Returns:
        Authenticated BigQuery client

    Raises:
        RuntimeError: If authentication fails
    """
    try:
        # Decrypt service account key (in production, use Secret Manager)
        # For now, assumes key is stored as plaintext JSON
        key_dict = json.loads(config.service_account_key_encrypted)

        credentials = service_account.Credentials.from_service_account_info(key_dict)
        client = bigquery.Client(
            project=config.gcp_project_id,
            credentials=credentials
        )

        return client

    except Exception as exc:
        raise RuntimeError(f"Failed to create BigQuery client: {str(exc)}")


async def run_gcp_ingest(settings: Settings) -> dict[str, Any]:
    """
    Main entry point for GCP cost ingestion (runs every 5 minutes).

    1. Fetches all enabled GcpCostIngestConfig records
    2. For each config, retrieves cost data from BigQuery
    3. Parses and upserts to CostDetail table
    4. Records job run status
    """
    db = SessionLocal()

    # Create JobRun record
    run = JobRun(
        tenant_id="platform",
        job_name="gcp_ingest",
        status="running"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # Fetch all enabled GCP configs
        configs = db.query(GcpCostIngestConfig).filter(
            GcpCostIngestConfig.enabled == True
        ).all()

        if not configs:
            logger.info("No GCP cost ingest configs found")
            run.status = "success"
            run.finished_at = utcnow()
            run.records_processed = 0
            run.details = {"message": "no_configs"}
            db.commit()
            return {"skipped": True, "reason": "no_configs"}

        total_records = 0
        errors = []

        for config in configs:
            try:
                records = await _ingest_for_gcp_config(db, config)
                total_records += records["inserted"] + records["updated"]
                logger.info(
                    f"Tenant {config.tenant_id}: "
                    f"{records['inserted']} inserted, "
                    f"{records['updated']} updated"
                )
            except Exception as exc:
                error_msg = f"Tenant {config.tenant_id}: {str(exc)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue processing other configs

        details = {
            "total_records": total_records,
            "configs_processed": len(configs),
            "errors": errors if errors else None,
        }

        status = "failed" if errors and total_records == 0 else "success"
        run.status = status
        run.finished_at = utcnow()
        run.records_processed = total_records
        run.details = details
        db.commit()

        return details

    except Exception as exc:
        logger.error(f"GCP ingest job failed: {str(exc)}")
        run.status = "failed"
        run.finished_at = utcnow()
        run.details = {"error": str(exc)}
        db.commit()
        raise
    finally:
        db.close()


async def _ingest_for_gcp_config(db: Session, config: GcpCostIngestConfig) -> dict[str, int]:
    """
    Process one GCP config:
    1. Authenticate with Service Account
    2. Query BigQuery for cost data
    3. Parse results
    4. Upsert to CostDetail
    """

    try:
        # Get BigQuery client
        client = get_bigquery_client(config)

        # Query cost data from last sync date
        timeframe_start = (config.last_synced_at or utcnow() - timedelta(days=1)).date()
        timeframe_end = utcnow().date()

        # BigQuery SQL for cost data
        # gcp_billing_export_v1 schema: https://cloud.google.com/billing/docs/how-to/export-data-bigquery
        sql = f"""
        SELECT
            CAST(SUBSTR(usage_start_time, 1, 10) AS STRING) as usage_date,
            service.description as service_name,
            sku.description as sku_description,
            COALESCE(location.location, resource.location, 'UNKNOWN') as resource_location,
            usage.amount_in_pricing_units as usage_amount,
            cost as cost_amount,
            project.id as project_id,
            labels
        FROM `{config.gcp_project_id}.{config.bq_dataset_id}.{config.bq_table_id}`
        WHERE CAST(SUBSTR(usage_start_time, 1, 10) AS DATE) >= '{timeframe_start}'
          AND CAST(SUBSTR(usage_start_time, 1, 10) AS DATE) < '{timeframe_end}'
          AND cost > 0
        LIMIT 100000
        """

        query_job = client.query(sql)
        results = query_job.result()

        records = _parse_gcp_results(db, results, config)

        # Update last sync time
        config.last_synced_at = utcnow()
        config.test_status = "success"
        config.test_message = f"Synced {records['inserted'] + records['updated']} records"
        db.commit()

        return records

    except Exception as exc:
        logger.error(f"GCP BigQuery error for tenant {config.tenant_id}: {str(exc)}")
        config.test_status = "failed"
        config.test_message = f"BigQuery error: {str(exc)}"
        db.commit()
        raise


def _parse_gcp_results(
    db: Session,
    results: Any,
    config: GcpCostIngestConfig
) -> dict[str, int]:
    """
    Parse BigQuery results and upsert to CostDetail.

    Transforms GCP billing export rows to CostDetail records.
    """

    inserted_count = 0
    updated_count = 0

    try:
        for row in results:
            try:
                # Extract fields from BigQuery row
                usage_date = str(row.usage_date or datetime.now().date()).strip()[:10]
                service_name = str(row.service_name or "Unknown").strip()
                sku_description = str(row.sku_description or "").strip()
                resource_location = str(row.resource_location or "").strip()
                usage_amount = Decimal(str(row.usage_amount_in_pricing_units or 0))
                cost_amount = Decimal(str(row.cost_amount or 0))
                project_id = str(row.project_id or "").strip()

                # Extract labels (GCP billing labels as JSON)
                labels = {}
                if hasattr(row, 'labels') and row.labels:
                    try:
                        labels = {item['key']: item['value'] for item in row.labels}
                    except (TypeError, KeyError):
                        labels = {}

                # Skip invalid records
                if not service_name or not usage_date:
                    logger.debug(f"Skipping invalid GCP record: service={service_name}, date={usage_date}")
                    continue

                # Check for duplicate
                existing = (
                    db.query(CostDetail)
                    .filter(
                        CostDetail.tenant_id == config.tenant_id,
                        CostDetail.account_id == project_id,
                        CostDetail.service == service_name,
                        CostDetail.resource_id == resource_location,
                        CostDetail.usage_start_date == usage_date,
                        CostDetail.sourced_from == "gcp",
                    )
                    .one_or_none()
                )

                tags = {
                    "ProjectId": project_id,
                    "Location": resource_location,
                    "SKU": sku_description,
                }
                tags.update(labels)

                if existing:
                    # Update existing record
                    existing.cost_after_discount = cost_amount
                    existing.usage_quantity = usage_amount
                    existing.tags = tags
                    existing.parsed_at = utcnow()
                    db.add(existing)
                    updated_count += 1
                else:
                    # Create new record
                    detail = CostDetail(
                        tenant_id=config.tenant_id,
                        account_id=project_id,
                        service=service_name,
                        sku=sku_description,
                        region=resource_location,
                        usage_type=sku_description,
                        usage_start_date=usage_date,
                        usage_end_date=usage_date,
                        usage_quantity=usage_amount,
                        rate=Decimal(0),
                        currency="USD",
                        cost_before_discount=cost_amount,
                        discount=Decimal(0),
                        cost_after_discount=cost_amount,
                        cost_with_tax=cost_amount,
                        resource_id=resource_location,
                        tags=tags,
                        sourced_from="gcp",
                        parsed_at=utcnow(),
                    )
                    db.add(detail)
                    inserted_count += 1

            except Exception as row_exc:
                logger.warning(f"Error processing GCP row: {str(row_exc)}")
                continue

        # Commit all records
        try:
            db.commit()
        except IntegrityError as exc:
            logger.warning(f"Integrity error during GCP upsert: {str(exc)}")
            db.rollback()
            # Retry with individual inserts
            for row in results:
                try:
                    usage_date = str(row.usage_date or "").strip()[:10]
                    service_name = str(row.service_name or "").strip()
                    resource_location = str(row.resource_location or "").strip()
                    project_id = str(row.project_id or "").strip()

                    if not service_name or not usage_date:
                        continue

                    existing = (
                        db.query(CostDetail)
                        .filter(
                            CostDetail.tenant_id == config.tenant_id,
                            CostDetail.account_id == project_id,
                            CostDetail.service == service_name,
                            CostDetail.usage_start_date == usage_date,
                            CostDetail.sourced_from == "gcp",
                        )
                        .one_or_none()
                    )

                    if not existing:
                        cost_amount = Decimal(str(row.cost_amount or 0))
                        usage_amount = Decimal(str(row.usage_amount_in_pricing_units or 0))
                        sku_description = str(row.sku_description or "").strip()

                        detail = CostDetail(
                            tenant_id=config.tenant_id,
                            account_id=project_id,
                            service=service_name,
                            sku=sku_description,
                            region=resource_location,
                            usage_type=sku_description,
                            usage_start_date=usage_date,
                            usage_end_date=usage_date,
                            usage_quantity=usage_amount,
                            rate=Decimal(0),
                            currency="USD",
                            cost_before_discount=cost_amount,
                            discount=Decimal(0),
                            cost_after_discount=cost_amount,
                            cost_with_tax=cost_amount,
                            resource_id=resource_location,
                            tags={"ProjectId": project_id, "Location": resource_location},
                            sourced_from="gcp",
                            parsed_at=utcnow(),
                        )
                        db.add(detail)
                        inserted_count += 1
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    pass

    except Exception as exc:
        logger.warning("GCP ingest outer error: %s", exc)
        db.rollback()

    return {"inserted": inserted_count, "updated": updated_count}


async def run_gcp_focus_transform(settings: Settings) -> dict[str, Any]:
    """
    Transform GCP CostDetail records to FOCUS format.
    Called by the main focus_transform job.
    """
    db = SessionLocal()

    try:
        from sqlalchemy import func

        # Get tenants with GCP cost data
        tenants = db.query(func.distinct(CostDetail.tenant_id)).filter(
            CostDetail.sourced_from == "gcp"
        ).all()

        total_focus_records = 0
        errors = []

        for (tenant_id,) in tenants:
            try:
                # Get unprocessed GCP CostDetail records
                cost_details = db.query(CostDetail).filter(
                    CostDetail.tenant_id == tenant_id,
                    CostDetail.sourced_from == "gcp"
                ).all()

                if not cost_details:
                    continue

                focus_count = 0
                for detail in cost_details:
                    try:
                        # Look up GCP service category mapping
                        category_mapping = db.query(ProductCategory).filter(
                            ProductCategory.tenant_id == tenant_id,
                            ProductCategory.provider == "GCP",
                            ProductCategory.service_name == detail.service,
                        ).first()

                        service_category = category_mapping.category if category_mapping else "Other"
                        usage_unit = category_mapping.unit_type if category_mapping else "hour"

                        # Check for existing FOCUS record
                        existing = db.query(FocusCost).filter(
                            FocusCost.tenant_id == tenant_id,
                            FocusCost.account_id == detail.account_id,
                            FocusCost.service_name == detail.service,
                            FocusCost.region == detail.region,
                            FocusCost.billing_period_start == detail.usage_start_date,
                        ).one_or_none()

                        chargeback_entity = (
                            detail.tags.get("CostCenter", "")
                            or detail.tags.get("Team", "")
                            or detail.tags.get("Environment", "default")
                        )

                        if existing:
                            existing.billed_cost = detail.cost_after_discount
                            existing.usage_quantity = detail.usage_quantity
                            existing.synth_date = utcnow()
                            db.add(existing)
                        else:
                            focus = FocusCost(
                                tenant_id=tenant_id,
                                account_id=detail.account_id,
                                billing_period_start=detail.usage_start_date,
                                invoice_issuer="gcp",
                                service_name=detail.service,
                                service_category=service_category,
                                sku=detail.sku,
                                region=detail.region,
                                usage_quantity=detail.usage_quantity,
                                usage_unit=usage_unit,
                                unit_price=Decimal(0),
                                billed_cost=detail.cost_after_discount,
                                currency="USD",
                                tags=detail.tags,
                                resource_id=detail.resource_id,
                                chargeback_entity=chargeback_entity,
                                synth_date=utcnow(),
                            )
                            db.add(focus)
                        focus_count += 1
                    except Exception as detail_exc:
                        logger.warning(f"Error transforming GCP detail: {str(detail_exc)}")
                        continue

                db.commit()
                total_focus_records += focus_count
                logger.info(f"Tenant {tenant_id}: {focus_count} GCP FOCUS records")

            except Exception as tenant_exc:
                logger.error(f"Error processing GCP tenant {tenant_id}: {str(tenant_exc)}")
                db.rollback()
                errors.append(f"Tenant {tenant_id}: {str(tenant_exc)}")

        return {
            "total_focus_records": total_focus_records,
            "tenants_processed": len(tenants),
            "errors": errors if errors else None,
        }

    except Exception as exc:
        logger.error(f"GCP FOCUS transform failed: {str(exc)}")
        raise
    finally:
        db.close()
