"""SQLAlchemy AsyncEngine factory for MedAI."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from medai.config import DatabaseConfig

__all__ = ["create_engine"]


def create_engine(config: DatabaseConfig) -> AsyncEngine:
    """Create a lazy async engine; no connection is opened until first query."""

    return create_async_engine(
        config.url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        # Keep sensitive SQL parameters (password hashes, tokens) out of logs and exceptions
        hide_parameters=True,
    )
