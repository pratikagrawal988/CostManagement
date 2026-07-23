"""
Azure Cost Management Ingestion

Handles integration with Azure Cost Management API and CSV exports:
1. Authenticates with Service Principal (OAuth)
2. Retrieves cost data from Azure Cost Management Export API
3. Parses and normalizes Azure cost data
4. Upserts to CostDetail table for FOCUS transformation
"""

import io
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .crypto import decrypt_secret
from .database import SessionLocal
from .jobs import tags_lookup, apply_tag_overrides
from .models import (
    AzureCostIngestConfig, CostDetail, CostAggregation,
    FocusCost, JobRun, ProductCategory, utcnow
)
from .settings import Settings

logger = logging.getLogger(__name__)

# Azure endpoints
AZURE_AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
AZURE_COST_MGMT_API = "https://management.azure.com"


def get_azure_access_token(config: AzureCostIngestConfig) -> str:
    """
    Obtain Azure OAuth access token using Service Principal credentials.

    Args:
        config: AzureCostIngestConfig with client credentials

    Returns:
        Access token string for API calls

    Raises:
        RuntimeError: If authentication fails
    """
    try:
        # client_secret lives in the encrypted `config` JSON blob (see crypto.py
        # and routes_credentials.py's upsert_azure_credential) — never as a
        # plaintext column.
        client_secret = decrypt_secret((config.config or {}).get("encrypted_secret", ""))
        if not client_secret:
            raise RuntimeError("No client secret configured for this Azure connection")

        token_url = AZURE_AUTH_URL.format(tenant_id=config.azure_tenant_id)

        payload = {
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": client_secret,
            "scope": "https://management.azure.com/.default",
        }

        response = requests.post(token_url, data=payload, timeout=30)
        response.raise_for_status()

        token_data = response.json()
        return token_data["access_token"]

    except Exception as exc:
        raise RuntimeError(f"Failed to obtain Azure token: {str(exc)}")


async def run_azure_ingest(settings: Settings) -> dict[str, Any]:
    """
    Main entry point for Azure cost ingestion (runs every 5 minutes).

    1. Fetches all enabled AzureCostIngestConfig records
    2. For each config, retrieves cost data from Azure Cost Management API
    3. Parses and upserts to CostDetail table
    4. Records job run status
    """
    db = SessionLocal()

    # Create JobRun record
    run = JobRun(
        tenant_id="platform",
        job_name="azure_ingest",
        status="running"
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # Fetch all enabled Azure configs
        configs = db.query(AzureCostIngestConfig).filter(
            AzureCostIngestConfig.enabled == True
        ).all()

        if not configs:
            logger.info("No Azure cost ingest configs found")
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
                records = await _ingest_for_azure_config(db, config)
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
        logger.error(f"Azure ingest job failed: {str(exc)}")
        run.status = "failed"
        run.finished_at = utcnow()
        run.details = {"error": str(exc)}
        db.commit()
        raise
    finally:
        db.close()


async def _ingest_for_azure_config(db: Session, config: AzureCostIngestConfig) -> dict[str, int]:
    """
    Process one Azure config:
    1. Authenticate with Service Principal
    2. Query Cost Management API for cost data
    3. Parse CSV response
    4. Upsert to CostDetail
    """

    try:
        # Get access token
        access_token = get_azure_access_token(config)

        # Build API request for cost data export
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Query cost data from the last sync date
        timeframe_start = (config.last_sync_at or utcnow() - timedelta(days=1)).date()
        timeframe_end = utcnow().date()

        # Construct API URL for Cost Management API query
        scope = f"/subscriptions/{config.subscription_id}"

        query_body = {
            "type": "Usage",
            "timeframe": "Custom",
            "timePeriod": {
                "from": f"{timeframe_start}T00:00:00Z",
                "to": f"{timeframe_end}T23:59:59Z",
            },
            "dataset": {
                "granularity": "Daily",
                "aggregation": {
                    "totalCost": {
                        "name": "PreTaxCost",
                        "function": "Sum",
                    }
                },
                "grouping": [
                    {"type": "Dimension", "name": "ServiceName"},
                    {"type": "Dimension", "name": "ResourceType"},
                    {"type": "Dimension", "name": "ResourceGroup"},
                    {"type": "Dimension", "name": "ResourceLocation"},
                    {"type": "Dimension", "name": "ChargeType"},
                ],
                "filter": {
                    "dimensions": {
                        "name": "ChargeType",
                        "operator": "In",
                        "values": ["Usage"],
                    }
                },
            },
        }

        # Call Cost Management Query API
        api_url = (
            f"{AZURE_COST_MGMT_API}{scope}/providers/Microsoft.CostManagement/query"
            f"?api-version=2021-10-01"
        )

        response = requests.post(
            api_url,
            json=query_body,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()

        cost_data = response.json()

        # Parse the response
        records = _parse_azure_cost_response(db, cost_data, config)

        # Update last sync time
        config.last_sync_at = utcnow()
        config.test_status = "success"
        config.test_message = f"Synced {records['inserted'] + records['updated']} records"
        db.commit()

        return records

    except requests.RequestException as exc:
        logger.error(f"Azure API error for tenant {config.tenant_id}: {str(exc)}")
        config.test_status = "failed"
        config.test_message = f"API error: {str(exc)}"
        db.commit()
        raise


def _parse_azure_cost_response(
    db: Session,
    response_data: dict,
    config: AzureCostIngestConfig
) -> dict[str, int]:
    """
    Parse Azure Cost Management API response and upsert to CostDetail.

    The API returns rows with dimensions and values. We transform these into
    CostDetail records compatible with our schema.
    """

    inserted_count = 0
    updated_count = 0

    try:
        rows = response_data.get("properties", {}).get("rows", [])
        columns = response_data.get("properties", {}).get("columns", [])

        if not rows or not columns:
            logger.warning("No cost data returned from Azure API")
            return {"inserted": 0, "updated": 0}

        # Build column index map
        column_map = {col["name"]: idx for idx, col in enumerate(columns)}

        for row in rows:
            try:
                # Extract dimensions and values
                # Row format: [dim1, dim2, ..., value1, value2, ...]

                # Get indices for standard columns
                service_idx = column_map.get("ServiceName")
                resource_type_idx = column_map.get("ResourceType")
                resource_group_idx = column_map.get("ResourceGroup")
                location_idx = column_map.get("ResourceLocation")
                cost_idx = column_map.get("PreTaxCost")
                usage_idx = column_map.get("UsageQuantity")
                date_idx = column_map.get("UsageDate")

                if cost_idx is None:
                    logger.debug("Cost column not found in row")
                    continue

                # Extract values
                service_name = str(row[service_idx] if service_idx else "Unknown").strip()
                resource_type = str(row[resource_type_idx] if resource_type_idx else "").strip()
                resource_group = str(row[resource_group_idx] if resource_group_idx else "").strip()
                location = str(row[location_idx] if location_idx else "").strip()
                cost_amount = Decimal(str(row[cost_idx] or 0))
                usage_qty = Decimal(str(row[usage_idx] or 0)) if usage_idx else Decimal(0)
                usage_date = str(row[date_idx] if date_idx else datetime.now().date()).strip()[:10]

                # Skip invalid records
                if not service_name or not usage_date:
                    logger.debug(f"Skipping invalid Azure record: service={service_name}, date={usage_date}")
                    continue

                # Check for duplicate
                existing = (
                    db.query(CostDetail)
                    .filter(
                        CostDetail.tenant_id == config.tenant_id,
                        CostDetail.account_id == config.subscription_id,
                        CostDetail.service == service_name,
                        CostDetail.resource_id == resource_group,
                        CostDetail.region == location,
                        CostDetail.usage_start_date == usage_date,
                        CostDetail.sourced_from == "azure",
                    )
                    .one_or_none()
                )

                tags = {
                    "ResourceGroup": resource_group,
                    "ResourceType": resource_type,
                    "Location": location,
                }

                if existing:
                    # Update existing record
                    existing.unblended_cost = float(cost_amount)
                    existing.blended_cost = float(cost_amount)
                    existing.amortised_cost = float(cost_amount)
                    existing.list_cost = float(cost_amount)
                    existing.usage_quantity = float(usage_qty)
                    existing.tags = tags
                    existing.parsed_at = utcnow()
                    db.add(existing)
                    updated_count += 1
                else:
                    # Create new record. Azure Cost Management's query API returns
                    # a single PreTaxCost figure (no separate blended/unblended/
                    # amortized breakdown like AWS CUR), so all three cost columns
                    # carry the same value here.
                    detail = CostDetail(
                        tenant_id=config.tenant_id,
                        account_id=config.subscription_id,
                        service=service_name,
                        sku=resource_type,
                        region=location,
                        usage_type=resource_type,
                        usage_start_date=usage_date,
                        usage_end_date=usage_date,
                        usage_quantity=float(usage_qty),
                        currency="USD",
                        unblended_cost=float(cost_amount),
                        blended_cost=float(cost_amount),
                        amortised_cost=float(cost_amount),
                        list_cost=float(cost_amount),
                        resource_id=resource_group,
                        tags=tags,
                        sourced_from="azure",
                        parsed_at=utcnow(),
                    )
                    db.add(detail)
                    inserted_count += 1

            except Exception as row_exc:
                logger.warning(f"Error processing Azure row: {str(row_exc)}")
                continue

        # Commit all records
        try:
            db.commit()
        except IntegrityError as exc:
            logger.warning(f"Integrity error during Azure upsert: {str(exc)}")
            db.rollback()
            # Retry with individual inserts
            for row in rows:
                try:
                    service_idx = column_map.get("ServiceName")
                    service_name = str(row[service_idx] if service_idx else "").strip()
                    location_idx = column_map.get("ResourceLocation")
                    location = str(row[location_idx] if location_idx else "").strip()
                    date_idx = column_map.get("UsageDate")
                    usage_date = str(row[date_idx] if date_idx else "").strip()[:10]
                    resource_group_idx = column_map.get("ResourceGroup")
                    resource_group = str(row[resource_group_idx] if resource_group_idx else "").strip()

                    if not service_name or not usage_date:
                        continue

                    existing = (
                        db.query(CostDetail)
                        .filter(
                            CostDetail.tenant_id == config.tenant_id,
                            CostDetail.account_id == config.subscription_id,
                            CostDetail.service == service_name,
                            CostDetail.region == location,
                            CostDetail.usage_start_date == usage_date,
                            CostDetail.sourced_from == "azure",
                        )
                        .one_or_none()
                    )

                    if not existing:
                        cost_idx = column_map.get("PreTaxCost")
                        cost_amount = Decimal(str(row[cost_idx] or 0))
                        resource_type_idx = column_map.get("ResourceType")
                        resource_type = str(row[resource_type_idx] if resource_type_idx else "").strip()

                        detail = CostDetail(
                            tenant_id=config.tenant_id,
                            account_id=config.subscription_id,
                            service=service_name,
                            sku=resource_type,
                            region=location,
                            usage_type=resource_type,
                            usage_start_date=usage_date,
                            usage_end_date=usage_date,
                            usage_quantity=0.0,
                            currency="USD",
                            unblended_cost=float(cost_amount),
                            blended_cost=float(cost_amount),
                            amortised_cost=float(cost_amount),
                            list_cost=float(cost_amount),
                            resource_id=resource_group,
                            tags={"ResourceType": resource_type, "Location": location},
                            sourced_from="azure",
                            parsed_at=utcnow(),
                        )
                        db.add(detail)
                        inserted_count += 1
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    pass

    except Exception as exc:
        logger.warning("Azure ingest outer error: %s", exc)
        db.rollback()

    return {"inserted": inserted_count, "updated": updated_count}


async def run_azure_focus_transform(settings: Settings) -> dict[str, Any]:
    """
    Transform Azure CostDetail records to FOCUS format (same as AWS).
    This is called by the main focus_transform job and applies FOCUS mappings
    to Azure cost data, enabling unified reporting across clouds.
    """
    db = SessionLocal()

    try:
        from sqlalchemy import func

        # Get tenants with Azure cost data
        tenants = db.query(func.distinct(CostDetail.tenant_id)).filter(
            CostDetail.sourced_from == "azure"
        ).all()

        total_focus_records = 0
        errors = []

        for (tenant_id,) in tenants:
            try:
                # Get unprocessed Azure CostDetail records
                cost_details = db.query(CostDetail).filter(
                    CostDetail.tenant_id == tenant_id,
                    CostDetail.sourced_from == "azure"
                ).all()

                if not cost_details:
                    continue

                focus_count = 0
                for detail in cost_details:
                    try:
                        # Look up Azure service category mapping
                        category_mapping = db.query(ProductCategory).filter(
                            ProductCategory.tenant_id == tenant_id,
                            ProductCategory.provider == "AZURE",
                            ProductCategory.service_name == detail.service,
                        ).first()

                        service_category = category_mapping.category if category_mapping else "Other"
                        usage_unit = category_mapping.unit_type if category_mapping else "hour"

                        tags = apply_tag_overrides(db, tenant_id, detail.resource_id, detail.tags or {})

                        # Check for existing FOCUS record (same grain as AWS: one
                        # row per sub-account + service + SKU + region + day)
                        existing = db.query(FocusCost).filter(
                            FocusCost.tenant_id == tenant_id,
                            FocusCost.sub_account_id == detail.account_id,
                            FocusCost.service_name == detail.service,
                            FocusCost.region_id == detail.region,
                            FocusCost.billing_period_start == detail.usage_start_date,
                        ).one_or_none()

                        list_unit_price = (detail.unblended_cost / detail.usage_quantity) if detail.usage_quantity else 0.0

                        if existing:
                            existing.billed_cost = detail.blended_cost
                            existing.effective_cost = detail.amortised_cost
                            existing.list_cost = detail.list_cost
                            existing.usage_quantity = detail.usage_quantity
                            existing.list_unit_price = list_unit_price
                            existing.tags = tags
                            existing.x_team = tags_lookup(tags, "Team", "team_name")
                            existing.x_cost_center = tags_lookup(tags, "CostCenter", "cost_center")
                            existing.x_app_id = tags_lookup(tags, "AppId", "Application", "app")
                            existing.x_environment = tags_lookup(tags, "Environment", "env", default="unknown")
                            existing.transformed_at = utcnow()
                            db.add(existing)
                        else:
                            focus = FocusCost(
                                tenant_id=tenant_id,
                                billing_account_id=detail.account_id,
                                sub_account_id=detail.account_id,
                                billing_period_start=detail.usage_start_date,
                                charge_period_start=f"{detail.usage_start_date}T00:00:00Z",
                                charge_category="Usage",
                                invoice_issuer_name="Microsoft Azure",
                                provider_name="Azure",
                                publisher_name="Microsoft",
                                service_name=detail.service,
                                service_category=service_category,
                                sku_id=detail.sku,
                                region_id=detail.region,
                                region_name=detail.region,
                                usage_quantity=detail.usage_quantity,
                                usage_unit=usage_unit,
                                pricing_category="Standard",
                                list_unit_price=list_unit_price,
                                list_cost=detail.list_cost,
                                billed_cost=detail.blended_cost,
                                effective_cost=detail.amortised_cost,
                                currency="USD",
                                tags=tags,
                                resource_id=detail.resource_id,
                                x_team=tags_lookup(tags, "Team", "team_name"),
                                x_cost_center=tags_lookup(tags, "CostCenter", "cost_center"),
                                x_app_id=tags_lookup(tags, "AppId", "Application", "app"),
                                x_environment=tags_lookup(tags, "Environment", "env", default="unknown"),
                                source_detail_id=detail.id,
                                transformed_at=utcnow(),
                            )
                            db.add(focus)
                        focus_count += 1
                    except Exception as detail_exc:
                        logger.warning(f"Error transforming Azure detail: {str(detail_exc)}")
                        continue

                db.commit()
                total_focus_records += focus_count
                logger.info(f"Tenant {tenant_id}: {focus_count} Azure FOCUS records")

            except Exception as tenant_exc:
                logger.error(f"Error processing Azure tenant {tenant_id}: {str(tenant_exc)}")
                db.rollback()
                errors.append(f"Tenant {tenant_id}: {str(tenant_exc)}")

        return {
            "total_focus_records": total_focus_records,
            "tenants_processed": len(tenants),
            "errors": errors if errors else None,
        }

    except Exception as exc:
        logger.error(f"Azure FOCUS transform failed: {str(exc)}")
        raise
    finally:
        db.close()
