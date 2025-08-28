"""
Database migration management for NeverMissCall shared library.

Provides SimpleMigrationManager for handling schema migrations
following the migration order defined in database-migration-order.md.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .connection import get_database

logger = logging.getLogger(__name__)


class SimpleMigrationManager:
    """
    Simple migration manager for PostgreSQL schema changes.
    
    Follows the single database architecture and migration order
    defined in the documentation.
    """
    
    def __init__(self, migrations_dir: str = "migrations"):
        """
        Initialize migration manager.
        
        Args:
            migrations_dir: Directory containing migration files
        """
        self.migrations_dir = Path(migrations_dir)
        self.db = get_database()
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(exist_ok=True)
    
    async def _ensure_migrations_table(self) -> None:
        """Create migrations tracking table if it doesn't exist."""
        sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                filename VARCHAR(255) NOT NULL,
                executed_at TIMESTAMP DEFAULT NOW(),
                checksum VARCHAR(64)
            )
        """
        await self.db.execute(sql)
    
    async def get_status(self) -> Dict[str, any]:
        """
        Get current migration status.
        
        Returns:
            Dictionary with migration status information
        """
        try:
            await self._ensure_migrations_table()
            
            # Get executed migrations
            executed_sql = "SELECT version, filename, executed_at FROM schema_migrations ORDER BY executed_at"
            executed = await self.db.query(executed_sql)
            
            # Get available migration files
            available = self._get_migration_files()
            
            # Calculate pending migrations
            executed_versions = {row['version'] for row in executed}
            pending = [f for f in available if self._extract_version(f.name) not in executed_versions]
            
            return {
                'executed': executed,
                'pending': [{'file': f.name, 'version': self._extract_version(f.name)} for f in pending],
                'total_executed': len(executed),
                'total_pending': len(pending)
            }
            
        except Exception as error:
            logger.error(f"Failed to get migration status: {error}")
            raise
    
    async def run_migrations(self) -> List[str]:
        """
        Run all pending migrations.
        
        Returns:
            List of executed migration filenames
        """
        try:
            await self._ensure_migrations_table()
            
            status = await self.get_status()
            pending = status['pending']
            
            if not pending:
                logger.info("No pending migrations found")
                return []
            
            executed = []
            
            for migration_info in pending:
                filename = migration_info['file']
                version = migration_info['version']
                
                logger.info(f"Executing migration: {filename}")
                
                migration_file = self.migrations_dir / filename
                await self._execute_migration_file(migration_file, version)
                executed.append(filename)
            
            logger.info(f"Successfully executed {len(executed)} migrations")
            return executed
            
        except Exception as error:
            logger.error(f"Migration execution failed: {error}")
            raise
    
    async def create_migration(self, name: str) -> str:
        """
        Create a new migration file.
        
        Args:
            name: Migration name (will be slugified)
            
        Returns:
            Created filename
        """
        try:
            # Generate version timestamp
            version = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # Clean name for filename
            clean_name = name.lower().replace(' ', '_').replace('-', '_')
            clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '_')
            
            filename = f"{version}_{clean_name}.sql"
            filepath = self.migrations_dir / filename
            
            # Create migration file with template
            template = f"""-- Migration: {name}
-- Created: {datetime.now().isoformat()}
-- Version: {version}

-- Add your SQL commands here
-- Example:
-- CREATE TABLE example (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMP DEFAULT NOW()
-- );

-- Remember to follow the database architecture patterns:
-- 1. All tables should have 'id' as UUID primary key
-- 2. Include 'created_at' and 'updated_at' timestamps
-- 3. Add 'tenant_id' for multi-tenant tables
-- 4. Use proper foreign key constraints
-- 5. Add indexes for performance

"""
            
            with open(filepath, 'w') as f:
                f.write(template)
            
            logger.info(f"Created migration file: {filename}")
            return filename
            
        except Exception as error:
            logger.error(f"Failed to create migration: {error}")
            raise
    
    def _get_migration_files(self) -> List[Path]:
        """Get all migration files sorted by version."""
        files = list(self.migrations_dir.glob("*.sql"))
        return sorted(files, key=lambda f: self._extract_version(f.name))
    
    def _extract_version(self, filename: str) -> str:
        """Extract version from migration filename."""
        return filename.split('_')[0]
    
    async def _execute_migration_file(self, filepath: Path, version: str) -> None:
        """
        Execute a single migration file.
        
        Args:
            filepath: Path to migration file
            version: Migration version
        """
        try:
            # Read migration file
            with open(filepath, 'r') as f:
                sql_content = f.read()
            
            # Split into individual statements (simple split on semicolon)
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            # Execute each statement
            for statement in statements:
                if statement and not statement.startswith('--'):
                    await self.db.execute(statement)
            
            # Record migration as executed
            record_sql = """
                INSERT INTO schema_migrations (version, filename, executed_at)
                VALUES ($1, $2, NOW())
            """
            await self.db.execute(record_sql, [version, filepath.name])
            
            logger.info(f"Successfully executed migration: {filepath.name}")
            
        except Exception as error:
            logger.error(f"Failed to execute migration {filepath.name}: {error}")
            raise
    
    async def rollback_migration(self, version: str) -> None:
        """
        Rollback a specific migration (basic implementation).
        
        Note: This is a simple implementation - complex rollbacks
        may require manual intervention.
        
        Args:
            version: Migration version to rollback
        """
        try:
            # Remove from migrations table
            sql = "DELETE FROM schema_migrations WHERE version = $1"
            result = await self.db.execute(sql, [version])
            
            if "DELETE 1" in result:
                logger.info(f"Rolled back migration version: {version}")
            else:
                logger.warning(f"Migration version {version} not found")
                
        except Exception as error:
            logger.error(f"Rollback failed for version {version}: {error}")
            raise