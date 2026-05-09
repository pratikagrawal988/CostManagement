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
    
    try:
        from .aws.routes import router as aws_router
        router.include_router(aws_router, prefix="/aws", tags=["aws"])
    except ImportError as e:
        print(f"⚠️  AWS router import error: {e}")
    
    try:
        from .azure.routes import router as azure_router
        router.include_router(azure_router, prefix="/azure", tags=["azure"])
    except ImportError as e:
        print(f"⚠️  Azure router import error: {e}")
    
    try:
        from .gcp.routes import router as gcp_router
        router.include_router(gcp_router, prefix="/gcp", tags=["gcp"])
    except ImportError as e:
        print(f"⚠️  GCP router import error: {e}")
    
    try:
        from .health.routes import router as health_router
        router.include_router(health_router, tags=["health"])
    except ImportError as e:
        print(f"⚠️  Health router import error: {e}")
    
    return router
