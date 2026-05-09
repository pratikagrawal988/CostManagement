from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import RecommendationDefinition, utcnow


ACTION_MAP = {
    "shutdown": "Shutdown",
    "rightsizesku": "RightsizeSku",
    "schedulepause": "SchedulePause",
    "tiermove": "TierMove",
    "deleteorphan": "DeleteOrphan",
    "volumetypeswap": "VolumeTypeSwap",
    "commitmentreview": "CommitmentReview",
    "tagfix": "TagFix",
    "budgetreview": "BudgetReview",
    "modelroute": "ModelRoute",
    "spotreview": "SpotReview",
    "licensereview": "LicenseReview",
}


METRIC_ALIASES = {
    "avg_cpu_pct": "compute.vm.cpu_utilisation_pct",
    "p95_cpu_pct": "compute.vm.cpu_utilisation_pct",
    "p95_mem_pct": "compute.vm.memory_utilisation_pct",
    "p95_network_pct": "compute.vm.network_utilisation_pct",
    "p95_network_out_mbps": "compute.vm.network_egress_mbps",
    "p95_network_out": "compute.vm.network_egress_mbps",
    "disk_iops": "storage.volume.iops",
    "avg_gpu_util_pct": "compute.gpu.utilisation_pct",
    "cache_hit_rate": "ai.llm.cache_hit_pct",
    "prompt_tokens": "ai.llm.prompt_tokens",
    "completion_tokens": "ai.llm.completion_tokens",
}


THRESHOLD_RE = re.compile(r"(?P<metric>[A-Za-z0-9_.:/ -]+)\s*(?P<op><=|>=|<|>|==|!=)\s*(?P<value>[-+]?\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class ParsedThreshold:
    metric: str
    canonical_signal: str
    operator: str
    value: float
    raw: str

    def as_dict(self) -> dict:
        return {
            "metric": self.metric,
            "signal": self.canonical_signal,
            "operator": self.operator,
            "value": self.value,
            "evidence_required": True,
            "raw": self.raw,
        }


def canonical_metric(metric: str) -> str:
    key = metric.strip().lower().replace(" ", "_").replace("%", "pct")
    key = key.replace("-", "_")
    return METRIC_ALIASES.get(key, key)


def parse_metric_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [canonical_metric(part) for part in re.split(r"[;,]", value) if part.strip()]


def parse_thresholds(value: str | None) -> list[dict]:
    if not value:
        return []
    thresholds: list[dict] = []
    for part in value.split(";"):
        raw = part.strip()
        match = THRESHOLD_RE.search(raw)
        if not match:
            continue
        metric = match.group("metric").strip()
        thresholds.append(
            ParsedThreshold(
                metric=metric,
                canonical_signal=canonical_metric(metric),
                operator=match.group("op"),
                value=float(match.group("value")),
                raw=raw,
            ).as_dict()
        )
    return thresholds


def normalize_action(value: str | None) -> str:
    if not value:
        return "CommitmentReview"
    collapsed = re.sub(r"[^A-Za-z0-9]", "", value).lower()
    return ACTION_MAP.get(collapsed, value.strip())


def row_to_definition(row: dict[str, str]) -> RecommendationDefinition:
    raw_metrics = row.get("primary_metrics", "")
    raw_thresholds = row.get("baseline_thresholds", "")
    third_party = [part.strip() for part in row.get("third_party_saas_options", "").split(";") if part.strip()]
    definition_id = row.get("id") or row.get("advisory_id")
    if not definition_id:
        raise ValueError("Recommendation row missing id")
    recommendation_type = normalize_action(row.get("recommendation_type"))
    return RecommendationDefinition(
        id=definition_id,
        name=row.get("recommendation_name", definition_id),
        category=row.get("category", "Other"),
        sub_category=row.get("sub_category", ""),
        provider_scope=row.get("provider_scope", "FinOps"),
        source_provider=row.get("source_provider", ""),
        recommendation_type=recommendation_type,
        priority=row.get("priority", "P2"),
        end_user_value=row.get("end_user_value", ""),
        implementation_complexity=row.get("implementation_complexity", ""),
        primary_metrics=parse_metric_list(raw_metrics),
        baseline_thresholds=parse_thresholds(raw_thresholds),
        lookback_window=row.get("lookback_window", "14d"),
        native_or_saas_data_source=row.get("native_or_saas_data_source", ""),
        third_party_saas_options=third_party,
        product_catalog_dependency=row.get("product_catalog_dependency", ""),
        compatibility_group=row.get("compatibility_group", ""),
        onboarding_to_engine=row.get("onboarding_to_engine", ""),
        basic_engine_support=row.get("basic_engine_support", ""),
        notes_and_guardrails=row.get("notes_and_guardrails", ""),
        enabled=True,
        config={
            "raw": row,
            "definition": row.get("recommendation_definition", ""),
            "expected_benefits": row.get("expected_benefits", ""),
            "configurator_showcase": row.get("configurator_showcase", ""),
            "advisory_source": row.get("advisory_source", ""),
            "advisory_id": row.get("advisory_id", ""),
            "advisory_layer": row.get("advisory_layer", ""),
        },
        imported_at=utcnow(),
    )


def import_catalog(db: Session, catalog_path: Path) -> dict[str, int | str]:
    imported = updated = skipped = 0
    if not catalog_path.exists():
        return {"imported": 0, "updated": 0, "skipped": 0, "path": str(catalog_path)}

    with catalog_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                definition = row_to_definition(row)
            except ValueError:
                skipped += 1
                continue
            existing = db.get(RecommendationDefinition, definition.id)
            if existing:
                for attr in (
                    "name",
                    "category",
                    "sub_category",
                    "provider_scope",
                    "source_provider",
                    "recommendation_type",
                    "priority",
                    "end_user_value",
                    "implementation_complexity",
                    "primary_metrics",
                    "baseline_thresholds",
                    "lookback_window",
                    "native_or_saas_data_source",
                    "third_party_saas_options",
                    "product_catalog_dependency",
                    "compatibility_group",
                    "onboarding_to_engine",
                    "basic_engine_support",
                    "notes_and_guardrails",
                    "config",
                ):
                    setattr(existing, attr, getattr(definition, attr))
                existing.imported_at = utcnow()
                updated += 1
            else:
                db.add(definition)
                imported += 1
    db.commit()
    return {"imported": imported, "updated": updated, "skipped": skipped, "path": str(catalog_path)}
