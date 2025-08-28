"""
Database connection management for NeverMissCall shared library.

Provides SimpleDatabase class and singleton connection management
following the patterns defined in the documentation.
"""

import asyncio
import asyncpg
import os
import logging
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

# Set up logging
logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration model following documentation patterns."""
    url: Optional[str] = None
    host: Optional[str] = 'localhost'
    port: Optional[int] = 5432
    database: Optional[str] = 'nevermisscall'
    username: Optional[str] = 'nevermisscall_user'
    password: Optional[str] = 'nevermisscall_admin411'
    max_connections: Optional[int] = 5
    
    def get_connection_string(self) -> str:
        """Build connection string from components."""
        if self.url:
            return self.url
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class SimpleDatabase:
    """
    Main database connection and query management class.
    
    Follows the single database architecture with shared connection pool
    as specified in database-architecture.md.
    """
    
    def __init__(self, config: Union[Dict, DatabaseConfig]):
        """Initialize database with configuration."""
        if isinstance(config, dict):
            self.config = DatabaseConfig(**config)
        else:
            self.config = config
        
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False
        
    async def connect(self) -> None:
        """
        Connect to PostgreSQL database with connection pooling.
        
        Creates connection pool as specified in the documentation for
        shared database access across all microservices.
        """
        if self._connected:
            return
            
        try:
            connection_string = self.config.get_connection_string()
            self.pool = await asyncpg.create_pool(
                connection_string,
                min_size=1,
                max_size=self.config.max_connections,
                command_timeout=30
            )
            self._connected = True
            logger.info(f"Connected to database: {self.config.database}")
            
        except Exception as error:
            logger.error(f"Database connection failed: {error}")
            raise ConnectionError(f"Failed to connect to database: {error}")
    
    async def query(self, sql: str, params: Optional[List] = None) -> Any:
        """
        Execute SQL query with optional parameters.
        
        Args:
            sql: SQL query string
            params: Optional list of parameters for parameterized queries
            
        Returns:
            Query results as list of records
        """
        if not self._connected or not self.pool:
            raise ConnectionError("Database not connected. Call connect() first.")
        
        try:
            async with self.pool.acquire() as connection:
                if params:
                    result = await connection.fetch(sql, *params)
                else:
                    result = await connection.fetch(sql)
                    
                # Convert asyncpg.Record to dict for easier handling
                return [dict(record) for record in result]
                
        except Exception as error:
            logger.error(f"Query execution failed: {error}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            raise
    
    async def execute(self, sql: str, params: Optional[List] = None) -> str:
        """
        Execute SQL command (INSERT, UPDATE, DELETE) with optional parameters.
        
        Args:
            sql: SQL command string
            params: Optional list of parameters
            
        Returns:
            Command status string
        """
        if not self._connected or not self.pool:
            raise ConnectionError("Database not connected. Call connect() first.")
            
        try:
            async with self.pool.acquire() as connection:
                if params:
                    result = await connection.execute(sql, *params)
                else:
                    result = await connection.execute(sql)
                return result
                
        except Exception as error:
            logger.error(f"Command execution failed: {error}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check database connectivity and health.
        
        Returns:
            True if database is healthy, False otherwise
        """
        try:
            if not self._connected or not self.pool:
                return False
                
            async with self.pool.acquire() as connection:
                result = await connection.fetchval("SELECT 1")
                return result == 1
                
        except Exception as error:
            logger.error(f"Health check failed: {error}")
            return False
    
    def get_pool(self) -> asyncpg.Pool:
        """Get the connection pool instance."""
        if not self.pool:
            raise ConnectionError("Database not connected. Call connect() first.")
        return self.pool
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("Database connection closed")


# Singleton database instance for shared access
_database_instance: Optional[SimpleDatabase] = None


def init_database(config: Union[Dict, DatabaseConfig]) -> SimpleDatabase:
    """
    Initialize singleton database instance.
    
    Args:
        config: Database configuration dict or DatabaseConfig object
        
    Returns:
        SimpleDatabase instance
    """
    global _database_instance
    
    if _database_instance is None:
        _database_instance = SimpleDatabase(config)
        logger.info("Database singleton initialized")
    
    return _database_instance


def get_database() -> SimpleDatabase:
    """
    Get existing database instance.
    
    Returns:
        SimpleDatabase singleton instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    global _database_instance
    
    if _database_instance is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return _database_instance


async def query(sql: str, params: Optional[List] = None) -> Any:
    """
    Direct query helper using singleton instance.
    
    Args:
        sql: SQL query string
        params: Optional parameters list
        
    Returns:
        Query results
    """
    db = get_database()
    return await db.query(sql, params)


async def health_check() -> bool:
    """
    Database health check using singleton instance.
    
    Returns:
        True if database is healthy
    """
    try:
        db = get_database()
        return await db.health_check()
    except Exception:
        return False


# Simple database object for compatibility
database = {
    'query': query,
    'health_check': health_check
}