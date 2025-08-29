"""Database service for user and session management."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
import asyncpg

from ..config.settings import database_config
from ..models.user import User, UserSession

logger = logging.getLogger(__name__)


class DatabaseService:
    """Handles database operations for users and sessions."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> bool:
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                database_config.url,
                min_size=database_config.pool_min,
                max_size=database_config.pool_max,
                server_settings={
                    'application_name': 'ts-auth-service',
                }
            )
            
            logger.info("Database connection pool initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    # User operations
    
    async def create_user(self, user_data: dict) -> Optional[User]:
        """Create a new user."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                INSERT INTO users (
                    email, password_hash, first_name, last_name, 
                    tenant_id, role, email_verified, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """
                
                row = await connection.fetchrow(
                    query,
                    user_data['email'],
                    user_data['password_hash'],
                    user_data['first_name'],
                    user_data['last_name'],
                    user_data.get('tenant_id'),
                    user_data.get('role', 'owner'),
                    user_data.get('email_verified', False),
                    user_data.get('is_active', True)
                )
                
                if row:
                    return User(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            async with self.pool.acquire() as connection:
                query = "SELECT * FROM users WHERE email = $1 AND is_active = true"
                row = await connection.fetchrow(query, email)
                
                if row:
                    return User(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        try:
            async with self.pool.acquire() as connection:
                query = "SELECT * FROM users WHERE id = $1 AND is_active = true"
                row = await connection.fetchrow(query, user_id)
                
                if row:
                    return User(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    async def update_user(self, user_id: UUID, update_data: dict) -> Optional[User]:
        """Update user information."""
        try:
            async with self.pool.acquire() as connection:
                # Build dynamic update query
                set_clauses = []
                params = []
                param_count = 1
                
                for field, value in update_data.items():
                    if field in ['first_name', 'last_name', 'email', 'tenant_id', 'email_verified']:
                        set_clauses.append(f"{field} = ${param_count}")
                        params.append(value)
                        param_count += 1
                
                # Always update the updated_at timestamp
                set_clauses.append(f"updated_at = ${param_count}")
                params.append(datetime.utcnow())
                param_count += 1
                
                # Add user_id for WHERE clause
                params.append(user_id)
                
                if not set_clauses:
                    return await self.get_user_by_id(user_id)
                
                query = f"""
                UPDATE users 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
                RETURNING *
                """
                
                row = await connection.fetchrow(query, *params)
                
                if row:
                    return User(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return None
    
    async def update_last_login(self, user_id: UUID) -> bool:
        """Update user's last login timestamp."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                UPDATE users 
                SET last_login_at = $1, updated_at = $1
                WHERE id = $2
                """
                
                result = await connection.execute(
                    query, 
                    datetime.utcnow(), 
                    user_id
                )
                
                return result == "UPDATE 1"
                
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """Deactivate a user account."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                UPDATE users 
                SET is_active = false, updated_at = $1
                WHERE id = $2
                """
                
                result = await connection.execute(
                    query,
                    datetime.utcnow(),
                    user_id
                )
                
                return result == "UPDATE 1"
                
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False
    
    # Session operations
    
    async def create_session(self, session_data: dict) -> Optional[UserSession]:
        """Create a new user session."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                INSERT INTO user_sessions (
                    user_id, refresh_token, device_info, ip_address, expires_at
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """
                
                row = await connection.fetchrow(
                    query,
                    session_data['user_id'],
                    session_data['refresh_token'],
                    session_data.get('device_info'),
                    session_data.get('ip_address'),
                    session_data['expires_at']
                )
                
                if row:
                    return UserSession(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None
    
    async def get_session_by_token(self, refresh_token: str) -> Optional[UserSession]:
        """Get session by refresh token."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                SELECT * FROM user_sessions 
                WHERE refresh_token = $1 AND is_active = true
                """
                
                row = await connection.fetchrow(query, refresh_token)
                
                if row:
                    return UserSession(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting session by token: {e}")
            return None
    
    async def invalidate_session(self, refresh_token: str) -> bool:
        """Invalidate a session by refresh token."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                UPDATE user_sessions 
                SET is_active = false 
                WHERE refresh_token = $1
                """
                
                result = await connection.execute(query, refresh_token)
                return result == "UPDATE 1"
                
        except Exception as e:
            logger.error(f"Error invalidating session: {e}")
            return False
    
    async def invalidate_user_sessions(self, user_id: UUID) -> int:
        """Invalidate all sessions for a user."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                UPDATE user_sessions 
                SET is_active = false 
                WHERE user_id = $1 AND is_active = true
                """
                
                result = await connection.execute(query, user_id)
                # Extract number from "UPDATE n" result
                return int(result.split()[-1]) if result else 0
                
        except Exception as e:
            logger.error(f"Error invalidating user sessions: {e}")
            return 0
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                DELETE FROM user_sessions 
                WHERE expires_at < $1 OR is_active = false
                """
                
                result = await connection.execute(query, datetime.utcnow())
                # Extract number from "DELETE n" result
                return int(result.split()[-1]) if result else 0
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0
    
    async def get_user_sessions(self, user_id: UUID) -> List[UserSession]:
        """Get active sessions for a user."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                SELECT * FROM user_sessions 
                WHERE user_id = $1 AND is_active = true
                ORDER BY created_at DESC
                """
                
                rows = await connection.fetch(query, user_id)
                return [UserSession(**dict(row)) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    # Utility methods
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        try:
            async with self.pool.acquire() as connection:
                query = "SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)"
                result = await connection.fetchval(query, email)
                return result
                
        except Exception as e:
            logger.error(f"Error checking email existence: {e}")
            return False
    
    async def get_user_count(self) -> int:
        """Get total number of users."""
        try:
            async with self.pool.acquire() as connection:
                query = "SELECT COUNT(*) FROM users WHERE is_active = true"
                result = await connection.fetchval(query)
                return result or 0
                
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
    
    async def get_active_session_count(self) -> int:
        """Get total number of active sessions."""
        try:
            async with self.pool.acquire() as connection:
                query = """
                SELECT COUNT(*) FROM user_sessions 
                WHERE is_active = true AND expires_at > $1
                """
                result = await connection.fetchval(query, datetime.utcnow())
                return result or 0
                
        except Exception as e:
            logger.error(f"Error getting active session count: {e}")
            return 0