"""
Database module for NeverMissCall shared library.

Provides SimpleDatabase class, connection management, and helper functions
for PostgreSQL database access across all microservices.
"""

from .connection import (
    SimpleDatabase,
    DatabaseConfig,
    init_database,
    get_database,
    query,
    health_check,
    database
)

from .repository import BaseRepository
from .migrations import SimpleMigrationManager

__all__ = [
    "SimpleDatabase",
    "DatabaseConfig",
    "init_database", 
    "get_database",
    "query",
    "health_check",
    "database",
    "BaseRepository",
    "SimpleMigrationManager"
]