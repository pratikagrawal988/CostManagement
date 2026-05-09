"""AWS cost ingestion API routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/aws")

# Routes for AWS configuration, cost ingestion, and management
# To be implemented: AWS credential management, cost pulling, data normalization
