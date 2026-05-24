"""
SQLAlchemy engine and session factory.

Reads DATABASE_URL from environment (set via .env or docker-compose).
Supports PostgreSQL (production) and SQLite (test/dev fallback).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://finops:finops@db:5432/finops_recommendations",
)

# Swap psycopg3 driver syntax for SQLite in tests
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """Create all tables defined in models (used in tests and fresh deploys)."""
    from . import models  # noqa: F401 — import to register all ORM classes
    Base.metadata.create_all(bind=engine)
