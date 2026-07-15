"""
Alert notification delivery — Slack webhooks + email (SMTP).

- POST/GET/PATCH/DELETE /api/notifications/channels   (budgets:write to modify)
- POST /api/notifications/channels/{id}/test          send a test message
- POST /api/notifications/check-budget-alerts         evaluate + dispatch now

A scheduled job (registered in main.py) runs the same check hourly. Alerts are
deduped per (budget, threshold, period window) via AlertNotification rows, so
a threshold fires once per period, not once per check.

Email uses SMTP_* env vars (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
SMTP_FROM, SMTP_TLS). Without SMTP_HOST, email sends are recorded as skipped.
"""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
from typing import Optional

import requests as _requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import TokenPayload
from .database import SessionLocal, get_db
from .models import AlertNotification, Budget, NotificationChannel, new_id, utcnow
from .rbac import record_audit, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ── Senders ───────────────────────────────────────────────────────────────────

def send_slack(webhook_url: str, text: str) -> dict:
    try:
        r = _requests.post(webhook_url, json={"text": text}, timeout=10)
        ok = r.status_code < 300
        return {"ok": ok, "detail": f"HTTP {r.status_code}" if not ok else "sent"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:200]}


def send_email(to_addr: str, subject: str, body: str) -> dict:
    host = os.getenv("SMTP_HOST", "")
    if not host:
        return {"ok": False, "detail": "SMTP_HOST not configured — email skipped"}
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_FROM", "finops-alerts@localhost")
        msg["To"] = to_addr
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=15) as s:
            if os.getenv("SMTP_TLS", "true").lower() == "true":
                s.starttls()
            user, pw = os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", "")
            if user:
                s.login(user, pw)
            s.send_message(msg)
        return {"ok": True, "detail": "sent"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:200]}


def dispatch(channel: NotificationChannel, subject: str, text: str) -> dict:
    if channel.type == "slack":
        return send_slack(channel.target, f"*{subject}*\n{text}")
    if channel.type == "email":
        return send_email(channel.target, subject, text)
    return {"ok": False, "detail": f"unknown channel type {channel.type}"}


# ── Budget alert check ────────────────────────────────────────────────────────

def check_budget_alerts(db: Session, tenant_id: str) -> dict:
    """Evaluate all enabled budgets; send + record alerts for newly crossed thresholds."""
    from .routes_budgets import _fmt, _latest_data_month  # local import, avoids cycle

    channels = db.query(NotificationChannel).filter(
        NotificationChannel.tenant_id == tenant_id,
        NotificationChannel.enabled.is_(True),
    ).all()

    anchor = _latest_data_month(db, tenant_id) or date.today()
    budgets = db.query(Budget).filter(
        Budget.tenant_id == tenant_id, Budget.enabled.is_(True)
    ).all()

    fired, skipped = [], 0
    for b in budgets:
        snap = _fmt(db, tenant_id, b, anchor)
        crossed = [t for t in (b.alert_thresholds or []) if snap["utilization_pct"] >= t]
        for threshold in crossed:
            exists = db.query(AlertNotification).filter(
                AlertNotification.budget_id == b.id,
                AlertNotification.threshold == threshold,
                AlertNotification.period_start == snap["window"]["start"],
            ).one_or_none()
            if exists:
                skipped += 1
                continue

            over = snap["utilization_pct"] >= 100
            subject = f"{'🔴' if over else '🟡'} Budget alert: {b.name} at {snap['utilization_pct']}%"
            text = (
                f"Budget '{b.name}' ({b.period}) has reached {snap['utilization_pct']}% "
                f"of {b.currency} {b.amount:,.0f} — actual {b.currency} {snap['actual']:,.0f} "
                f"for {snap['window']['start']} → {snap['window']['end']}. "
                f"Run-rate forecast: {b.currency} {snap['forecast_eop']:,.0f} ({snap['forecast_pct']}%). "
                f"Threshold crossed: {threshold}%."
            )
            results = [{"channel": c.name or c.type, **dispatch(c, subject, text)} for c in channels]

            db.add(AlertNotification(
                id=new_id(),
                tenant_id=tenant_id,
                budget_id=b.id,
                threshold=threshold,
                period_start=snap["window"]["start"],
                utilization_pct=snap["utilization_pct"],
                message=text,
                results=results,
            ))
            db.commit()
            fired.append({
                "budget": b.name, "threshold": threshold,
                "utilization_pct": snap["utilization_pct"],
                "channels": results,
            })
    return {"checked": len(budgets), "fired": fired, "deduped": skipped,
            "channels_configured": len(channels)}


async def run_budget_alert_check(settings=None) -> None:
    """Scheduler entrypoint — checks every tenant that has budgets."""
    db = SessionLocal()
    try:
        tenants = [t[0] for t in db.query(Budget.tenant_id).distinct().all()]
        for tid in tenants:
            try:
                out = check_budget_alerts(db, tid)
                if out["fired"]:
                    logger.info("Budget alerts fired for %s: %s", tid, len(out["fired"]))
            except Exception:
                logger.exception("Budget alert check failed for tenant %s", tid)
    finally:
        db.close()


# ── Channel CRUD ──────────────────────────────────────────────────────────────

class ChannelRequest(BaseModel):
    type: str                 # slack | email
    name: str = ""
    target: str               # webhook URL or email address
    enabled: bool = True


def _fmt_channel(c: NotificationChannel) -> dict:
    target = c.target
    if c.type == "slack" and len(target) > 40:   # don't echo full webhook URLs
        target = target[:34] + "…"
    return {"id": c.id, "type": c.type, "name": c.name, "target": target,
            "enabled": c.enabled, "created_at": c.created_at.isoformat()}


@router.get("/channels")
def list_channels(
    current: TokenPayload = Depends(require_permission("budgets:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(NotificationChannel).filter(
        NotificationChannel.tenant_id == current.tenant_id
    ).order_by(NotificationChannel.created_at).all()
    return {"count": len(rows), "channels": [_fmt_channel(c) for c in rows]}


@router.post("/channels", status_code=201)
def create_channel(
    req: ChannelRequest,
    current: TokenPayload = Depends(require_permission("budgets:write")),
    db: Session = Depends(get_db),
):
    if req.type not in ("slack", "email"):
        raise HTTPException(400, "type must be 'slack' or 'email'")
    if req.type == "slack" and not req.target.startswith("https://hooks.slack.com/"):
        raise HTTPException(400, "Slack target must be an incoming webhook URL (https://hooks.slack.com/…)")
    if req.type == "email" and "@" not in req.target:
        raise HTTPException(400, "Email target must be an email address")

    c = NotificationChannel(
        id=new_id(), tenant_id=current.tenant_id, type=req.type,
        name=req.name or req.type, target=req.target, enabled=req.enabled,
    )
    db.add(c)
    db.commit()
    record_audit(db, current, action="notification_channel.create", resource_type="channel",
                 resource_id=c.id, detail={"type": c.type, "name": c.name})
    return _fmt_channel(c)


@router.delete("/channels/{channel_id}")
def delete_channel(
    channel_id: str,
    current: TokenPayload = Depends(require_permission("budgets:write")),
    db: Session = Depends(get_db),
):
    c = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current.tenant_id,
    ).one_or_none()
    if not c:
        raise HTTPException(404, "Channel not found")
    db.delete(c)
    db.commit()
    record_audit(db, current, action="notification_channel.delete", resource_type="channel",
                 resource_id=channel_id)
    return {"status": "deleted", "id": channel_id}


@router.post("/channels/{channel_id}/test")
def test_channel(
    channel_id: str,
    current: TokenPayload = Depends(require_permission("budgets:write")),
    db: Session = Depends(get_db),
):
    c = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.tenant_id == current.tenant_id,
    ).one_or_none()
    if not c:
        raise HTTPException(404, "Channel not found")
    result = dispatch(c, "FinOps test notification",
                      "This is a test from your FinOps platform — channel is wired up correctly.")
    return {"channel": c.name or c.type, **result}


@router.post("/check-budget-alerts")
def trigger_budget_alerts(
    current: TokenPayload = Depends(require_permission("budgets:read")),
    db: Session = Depends(get_db),
):
    out = check_budget_alerts(db, current.tenant_id)
    record_audit(db, current, action="budget_alerts.check", resource_type="budgets",
                 resource_id="batch", detail={"fired": len(out["fired"]), "deduped": out["deduped"]})
    return out


@router.get("/history")
def alert_history(
    current: TokenPayload = Depends(require_permission("budgets:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(AlertNotification).filter(
        AlertNotification.tenant_id == current.tenant_id
    ).order_by(AlertNotification.created_at.desc()).limit(50).all()
    return {"count": len(rows), "alerts": [
        {"id": a.id, "budget_id": a.budget_id, "threshold": a.threshold,
         "period_start": a.period_start, "utilization_pct": a.utilization_pct,
         "message": a.message, "results": a.results, "created_at": a.created_at.isoformat()}
        for a in rows
    ]}
