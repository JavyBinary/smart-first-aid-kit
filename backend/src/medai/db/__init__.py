"""MedAI database module."""

from medai.db.engine import create_engine
from medai.db.tables import metadata

__all__ = ["create_engine", "metadata"]
