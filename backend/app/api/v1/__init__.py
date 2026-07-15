"""API v1 routes"""
from fastapi import APIRouter

def get_api_router():
    """Register all API routers and return combined router"""
    router = APIRouter(prefix="/api/v1")
    
    try:
        from .cost.routes import router as cost_router
        router.include_router(cost_router, tags=["cost"])
    except ImportError as e:
        print(f"⚠️  Cost router import error: {e}")
    
    # NOTE: aws/azure/gcp route modules already declare their own prefix
    # (e.g. APIRouter(prefix="/azure")). Passing prefix= again here produced
    # double-prefixed paths like /api/v1/azure/azure/ingest-config.
    try:
        from .aws.routes import router as aws_router
        router.include_router(aws_router, tags=["aws"])
    except ImportError as e:
        print(f"⚠️  AWS router import error: {e}")

    try:
        from .azure.routes import router as azure_router
        router.include_router(azure_router, tags=["azure"])
    except ImportError as e:
        print(f"⚠️  Azure router import error: {e}")

    try:
        from .gcp.routes import router as gcp_router
        router.include_router(gcp_router, tags=["gcp"])
    except ImportError as e:
        print(f"⚠️  GCP router import error: {e}")
    
    try:
        from .health.routes import router as health_router
        router.include_router(health_router, tags=["health"])
    except ImportError as e:
        print(f"⚠️  Health router import error: {e}")
    
    return router
