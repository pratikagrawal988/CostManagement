"""
Demo AI cost seeder — inserts 90 days of realistic AI spend into focus_cost.

Vendor mix (approximate):
  Anthropic Claude API     ~40%  (claude-3-5-sonnet, claude-3-haiku, claude-3-opus)
  OpenAI                   ~28%  (gpt-4o, gpt-4o-mini, text-embedding-3-small)
  AWS Bedrock (Claude)     ~14%  (via bedrock wrapper — same models)
  Google Vertex AI          ~8%  (gemini-1.5-pro, gemini-1.5-flash)
  Cohere                    ~5%  (command-r-plus, embed-english)

Team distribution: platform (30%), product (25%), data (20%), growth (15%), infra (10%)
App distribution: chat-api, code-assist, support-bot, embeddings-svc, analytics

Also seeds:
  - saas_tool_allocations  (Cursor, GitHub Copilot, Tabnine seats)
  - app_cost_attributions  (one row per app per model per day)
"""

from __future__ import annotations

import random
from datetime import date, timedelta, timezone, datetime
from typing import List

from sqlalchemy.orm import Session

from .models import (
    FocusCost,
    SaaSToolAllocation,
    AppCostAttribution,
    new_id,
    utcnow,
)

# ── Constants ──────────────────────────────────────────────────────────────────

SEED_DAYS = 90

TEAMS        = ["platform", "product", "data-science", "growth", "infra"]
TEAM_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

APPS        = ["chat-api", "code-assist", "support-bot", "embeddings-svc", "analytics-pipeline"]
APP_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

ENVS        = ["production", "staging", "development"]
ENV_WEIGHTS = [0.70, 0.20, 0.10]

COST_CENTERS = ["CC-1010", "CC-2020", "CC-3030", "CC-4040"]

# (vendor, model, tier, $/1M_input, $/1M_output, avg_daily_requests, cache_hit_rate)
MODEL_CATALOG = [
    # Anthropic
    ("anthropic", "claude-3-5-sonnet-20241022", "premium",  3.00,  15.00, 2800, 0.22),
    ("anthropic", "claude-3-haiku-20240307",    "budget",   0.25,   1.25, 5200, 0.15),
    ("anthropic", "claude-3-opus-20240229",     "premium", 15.00,  75.00,  380, 0.30),
    # OpenAI
    ("openai",    "gpt-4o-2024-11-20",          "premium",  2.50,  10.00, 1900, 0.18),
    ("openai",    "gpt-4o-mini-2024-07-18",     "budget",   0.15,   0.60, 4100, 0.12),
    ("openai",    "text-embedding-3-small",     "embed",    0.02,   0.00, 8500, 0.05),
    ("openai",    "text-embedding-3-large",     "embed",    0.13,   0.00, 1200, 0.05),
    # AWS Bedrock
    ("aws",       "anthropic.claude-3-sonnet",  "premium",  3.00,  15.00,  950, 0.10),
    ("aws",       "anthropic.claude-3-haiku",   "budget",   0.25,   1.25, 1400, 0.10),
    ("aws",       "amazon.titan-embed-text-v2", "embed",    0.02,   0.00, 2200, 0.05),
    # Google Vertex
    ("google",    "gemini-1.5-pro",             "premium",  3.50,  10.50,  450, 0.15),
    ("google",    "gemini-1.5-flash",           "budget",   0.075,  0.30, 1800, 0.12),
    # Cohere
    ("cohere",    "command-r-plus",             "premium",  3.00,  15.00,  280, 0.20),
    ("cohere",    "embed-english-v3.0",         "embed",    0.10,   0.00,  900, 0.05),
]

SAAS_TOOLS = [
    {"tool": "Cursor",          "seats": 38, "monthly_per_seat": 20.00},
    {"tool": "GitHub Copilot",  "seats": 52, "monthly_per_seat": 19.00},
    {"tool": "Tabnine",         "seats": 12, "monthly_per_seat": 12.00},
]

SAAS_USERS = [
    "alice", "bob", "carol", "dave", "eve",
    "frank", "grace", "hank", "iris", "jack",
]


def _rng(d: date) -> random.Random:
    return random.Random(int(d.strftime("%Y%m%d")) + 42)


def _make_focus_row(
    *,
    tenant_id:     str,
    billing_date:  date,
    vendor:        str,
    model:         str,
    tier:          str,
    price_in:      float,
    price_out:     float,
    requests:      int,
    cache_rate:    float,
    team:          str,
    app:           str,
    env:           str,
    cost_center:   str,
    rng:           random.Random,
) -> FocusCost:
    if tier == "embed":
        in_tok  = requests * rng.randint(200, 800)
        out_tok = 0
    elif tier == "premium":
        in_tok  = requests * rng.randint(500, 2000)
        out_tok = requests * rng.randint(200, 800)
    else:
        in_tok  = requests * rng.randint(200, 1000)
        out_tok = requests * rng.randint(50,  400)

    cache_r = int(in_tok * cache_rate * 0.5)
    cache_w = int(in_tok * cache_rate * 0.2)
    billed_in  = in_tok - cache_r

    cost = (
        (billed_in  / 1_000_000 * price_in)
      + (out_tok    / 1_000_000 * price_out)
      + (cache_r    / 1_000_000 * price_in  * 0.10)
      + (cache_w    / 1_000_000 * price_in  * 0.25)
    ) * rng.uniform(0.92, 1.08)
    cost = round(cost, 6)

    iso_date = billing_date.isoformat()
    iso_end  = (billing_date + timedelta(days=1)).isoformat()

    return FocusCost(
        id                           = new_id(),
        tenant_id                    = tenant_id,
        # FOCUS required — string ISO dates
        billing_account_id           = f"{tenant_id}-billing",
        billing_account_name         = "Demo Tenant Billing",
        billing_period_start         = iso_date,
        billing_period_end           = iso_end,
        charge_period_start          = f"{iso_date}T00:00:00Z",
        charge_period_end            = f"{iso_end}T00:00:00Z",
        charge_category              = "Usage",
        invoice_issuer_name          = vendor.title(),
        provider_name                = vendor,
        publisher_name               = vendor,
        service_name                 = f"{vendor} AI API",
        service_category             = "AI and Machine Learning",
        sku_id                       = f"{vendor}::{model}",
        sku_price_id                 = f"{vendor}::{model}::standard",
        region_id                    = rng.choice(["us-east-1", "us-west-2", "eu-west-1"]),
        region_name                  = rng.choice(["US East", "US West", "EU West"]),
        resource_id                  = f"{vendor}/{model}/{team}",
        resource_name                = f"{model}-{app}",
        resource_type                = "LLM_API",
        resource_status              = "Running",
        sub_account_id               = f"{tenant_id}-{team}",
        sub_account_name             = f"Team {team}",
        pricing_category             = "Standard",
        pricing_quantity             = float(in_tok + out_tok),
        pricing_unit                 = "tokens",
        usage_quantity               = float(requests),
        usage_unit                   = "requests",
        list_unit_price              = price_in / 1_000_000,
        list_cost                    = round(cost * rng.uniform(1.00, 1.05), 6),
        billed_cost                  = cost,
        effective_cost               = cost,
        contracted_cost              = cost,
        contracted_unit_price        = price_in / 1_000_000,
        commitment_discount_id       = "",
        commitment_discount_name     = "",
        commitment_discount_category = "",
        commitment_discount_type     = "",
        commitment_discount_status   = "",
        currency                     = "USD",
        tags                         = {"team": team, "app": app, "env": env, "cost_center": cost_center},
        # AI extension columns
        x_ai_vendor                  = vendor,
        x_ai_model                   = model,
        x_ai_tier                    = tier,
        x_input_tokens               = float(in_tok),
        x_output_tokens              = float(out_tok),
        x_cache_read_tokens          = float(cache_r),
        x_cache_write_tokens         = float(cache_w),
        x_request_count              = requests,
        x_team                       = team,
        x_app_id                     = app,
        x_cost_center                = cost_center,
        x_environment                = env,
    )


def seed_ai_demo_data(db: Session, tenant_id: str = "tenant-demo") -> dict:
    """
    Idempotent: skips if AI focus_cost rows already exist for this tenant.
    """
    existing = (
        db.query(FocusCost)
        .filter(FocusCost.tenant_id == tenant_id)
        .filter(FocusCost.x_ai_vendor != "")
        .first()
    )
    if existing:
        return {"status": "skipped", "reason": "AI demo data already present"}

    today     = date.today()
    start_day = today - timedelta(days=SEED_DAYS - 1)

    rows: List[FocusCost] = []

    for day_offset in range(SEED_DAYS):
        billing_date   = start_day + timedelta(days=day_offset)
        rng            = _rng(billing_date)
        is_weekend     = billing_date.weekday() >= 5
        traffic_factor = 0.35 if is_weekend else 1.0
        growth         = 1.0 + (day_offset * 0.0008)

        for (vendor, model, tier, p_in, p_out, base_req, cache_rate) in MODEL_CATALOG:
            daily_req = int(base_req * traffic_factor * growth * rng.uniform(0.80, 1.20))
            if daily_req < 1:
                continue

            for i, team in enumerate(TEAMS):
                team_share = TEAM_WEIGHTS[i] * rng.uniform(0.85, 1.15)
                team_req   = max(1, int(daily_req * team_share))
                app        = rng.choices(APPS,  weights=APP_WEIGHTS)[0]
                env        = rng.choices(ENVS,  weights=ENV_WEIGHTS)[0]
                cc         = rng.choice(COST_CENTERS)

                rows.append(_make_focus_row(
                    tenant_id    = tenant_id,
                    billing_date = billing_date,
                    vendor       = vendor,
                    model        = model,
                    tier         = tier,
                    price_in     = p_in,
                    price_out    = p_out,
                    requests     = team_req,
                    cache_rate   = cache_rate,
                    team         = team,
                    app          = app,
                    env          = env,
                    cost_center  = cc,
                    rng          = rng,
                ))

        if len(rows) >= 5000:
            db.bulk_save_objects(rows)
            db.flush()
            rows = []

    if rows:
        db.bulk_save_objects(rows)
        db.flush()

    _seed_saas_allocations(db, tenant_id, today)
    _seed_app_attributions(db, tenant_id, today)

    db.commit()
    return {
        "status": "seeded",
        "days": SEED_DAYS,
        "models": len(MODEL_CATALOG),
        "teams": len(TEAMS),
    }


# ── SaaS seat allocations ─────────────────────────────────────────────────────

def _seed_saas_allocations(db: Session, tenant_id: str, today: date):
    existing = db.query(SaaSToolAllocation).filter_by(tenant_id=tenant_id).first()
    if existing:
        return

    rng    = random.Random(777)
    period = today.strftime("%Y-%m")

    for tool_cfg in SAAS_TOOLS:
        for idx, user in enumerate(SAAS_USERS):
            if idx >= tool_cfg["seats"] % len(SAAS_USERS) + 3:
                break
            roll = rng.random()
            if roll > 0.35:
                last_active = today - timedelta(days=rng.randint(0, 1))
                minutes     = rng.randint(60, 480)
                active      = True
            elif roll > 0.15:
                last_active = today - timedelta(days=rng.randint(2, 7))
                minutes     = rng.randint(5, 59)
                active      = True
            else:
                last_active = today - timedelta(days=rng.randint(8, 45))
                minutes     = 0
                active      = False

            db.add(SaaSToolAllocation(
                id            = new_id(),
                tenant_id     = tenant_id,
                tool_name     = tool_cfg["tool"],
                vendor        = tool_cfg["tool"],
                user_id       = user,
                user_email    = f"{user}@company.com",
                team          = rng.choice(TEAMS),
                period        = period,
                seat_cost     = tool_cfg["monthly_per_seat"],
                usage_minutes = minutes,
                completions   = rng.randint(0, 2000) if minutes > 0 else 0,
                active        = active,
                last_active_at= datetime(last_active.year, last_active.month, last_active.day, tzinfo=timezone.utc),
            ))
    db.flush()


# ── App cost attributions ─────────────────────────────────────────────────────

def _seed_app_attributions(db: Session, tenant_id: str, today: date):
    existing = db.query(AppCostAttribution).filter_by(tenant_id=tenant_id).first()
    if existing:
        return

    rng = random.Random(888)
    # Seed last 30 days of app attribution summaries
    for day_offset in range(30):
        d   = today - timedelta(days=day_offset)
        iso = d.isoformat()

        # Pick a subset of models per app per day
        for app_idx, app in enumerate(APPS):
            for vendor, model, tier, p_in, p_out, base_req, _ in MODEL_CATALOG[:6]:
                # Only assign this model to ~2/5 of apps per day
                if rng.random() > 0.40:
                    continue
                is_weekend = d.weekday() >= 5
                reqs       = int(base_req * APP_WEIGHTS[app_idx] * (0.35 if is_weekend else 1.0) * rng.uniform(0.8, 1.2))
                if reqs < 1:
                    continue
                in_tok  = reqs * rng.randint(300, 1200)
                out_tok = reqs * rng.randint(50, 400) if tier != "embed" else 0
                cost    = round((in_tok / 1_000_000 * p_in) + (out_tok / 1_000_000 * p_out), 4)

                db.add(AppCostAttribution(
                    id             = new_id(),
                    tenant_id      = tenant_id,
                    app_id         = app,
                    app_name       = app.replace("-", " ").title(),
                    team           = rng.choice(TEAMS),
                    ai_vendor      = vendor,
                    ai_model       = model,
                    date           = iso,
                    daily_cost     = cost,
                    request_count  = reqs,
                    input_tokens   = float(in_tok),
                    output_tokens  = float(out_tok),
                    avg_latency_ms = rng.randint(80, 900),
                    error_rate     = rng.uniform(0.001, 0.04),
                ))

    db.flush()
