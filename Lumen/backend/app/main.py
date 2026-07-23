"""
Lumen FinOps OS — FastAPI application entry point.

Mounts all routers and starts the APScheduler background job runner.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_all_tables
from .settings import Settings

logger = logging.getLogger(__name__)

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    # 1. Ensure all ORM tables exist (idempotent)
    try:
        create_all_tables()
        logger.info("Database tables verified / created.")
    except Exception as exc:
        logger.warning("Could not run create_all_tables: %s", exc)

    # 2. Seed reference data + AI demo data (idempotent)
    try:
        from .database import SessionLocal
        from .seed import seed_everything
        db = SessionLocal()
        result = await seed_everything(db, settings)
        db.close()
        logger.info("Seed complete: %s", result)
    except Exception as exc:
        logger.warning("Seed skipped: %s", exc)

    # 3. Start background scheduler (SCHEDULER_ENABLED env var controls this)
    scheduler = None
    try:
        from .jobs import start_scheduler
        scheduler = start_scheduler(settings)
        if scheduler:
            logger.info(
                "Scheduler started — jobs: %s",
                [job.id for job in scheduler.get_jobs()],
            )
        else:
            logger.info("Scheduler disabled (SCHEDULER_ENABLED=false).")
    except Exception as exc:
        logger.warning("Scheduler failed to start: %s", exc)

    yield   # ← application runs here

    # 4. Graceful shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Lumen FinOps OS",
    description="Cloud cost intelligence and AI cost management platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
from .routes_cost        import router as cost_router
from .routes_azure       import router as azure_router
from .routes_gcp         import router as gcp_router
from .routes_ai          import router as ai_router
from .routes_credentials import router as credentials_router
from .routes_auth        import router as auth_router
from .routes_overview    import router as overview_router
from .routes_explorer    import router as explorer_router
from .routes_admin       import router as admin_router
from .routes_reco        import router as reco_router
from .routes_users       import router as users_router, audit_router
from .routes_budgets     import router as budgets_router
from .routes_tags        import router as tags_router
from .routes_databricks  import router as databricks_router
from .cost_recommendations import router as cost_reco_router
from .notifications import router as notifications_router

app.include_router(auth_router)
app.include_router(cost_router)
app.include_router(azure_router)
app.include_router(gcp_router)
app.include_router(ai_router)
app.include_router(credentials_router)
app.include_router(overview_router)
app.include_router(explorer_router)
app.include_router(admin_router)
app.include_router(reco_router)
app.include_router(users_router)
app.include_router(audit_router)
app.include_router(budgets_router)
app.include_router(tags_router)
app.include_router(databricks_router)
app.include_router(cost_reco_router)
app.include_router(notifications_router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["platform"])
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["platform"])
def root():
    return {"message": "Lumen FinOps OS API", "docs": "/docs"}
