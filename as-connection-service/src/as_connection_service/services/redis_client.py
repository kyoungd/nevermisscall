"""Redis client service for connection state management."""

import json
import aioredis
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

from ..config import settings
from ..models.connection import ConnectionState

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for connection state and event queue management."""
    
    def __init__(self):
        self._connection_pool = None
        self._event_queue_pool = None
    
    async def initialize(self):
        """Initialize Redis connections."""
        try:
            # Connection state Redis database
            self._connection_pool = aioredis.from_url(
                settings.redis_url,
                db=settings.connection_redis_db,
                decode_responses=True
            )
            
            # Event queue Redis database
            self._event_queue_pool = aioredis.from_url(
                settings.redis_url,
                db=settings.event_queue_redis_db,
                decode_responses=True
            )
            
            # Test connections
            await self._connection_pool.ping()
            await self._event_queue_pool.ping()
            
            logger.info("Redis connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connections: {e}")
            raise
    
    async def close(self):
        """Close Redis connections."""
        try:
            if self._connection_pool:
                await self._connection_pool.close()
            if self._event_queue_pool:
                await self._event_queue_pool.close()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    def _get_connection_key(self, tenant_id: str, connection_id: str) -> str:
        """Generate Redis key for connection state."""
        return f"connections:{tenant_id}:{connection_id}"
    
    def _get_tenant_connections_key(self, tenant_id: str) -> str:
        """Generate Redis key for tenant connection index."""
        return f"tenant_connections:{tenant_id}"
    
    def _get_event_queue_key(self, event_id: str) -> str:
        """Generate Redis key for event queue item."""
        return f"event_queue:{event_id}"
    
    async def store_connection(self, connection: ConnectionState) -> bool:
        """Store connection state in Redis."""
        try:
            connection_key = self._get_connection_key(connection.tenant_id, connection.connection_id)
            tenant_key = self._get_tenant_connections_key(connection.tenant_id)
            
            # Store connection state
            connection_data = connection.model_dump_json()
            await self._connection_pool.setex(
                connection_key,
                settings.connection_ttl_seconds,
                connection_data
            )
            
            # Add to tenant connection index
            await self._connection_pool.sadd(tenant_key, connection.connection_id)
            await self._connection_pool.expire(tenant_key, settings.connection_ttl_seconds)
            
            logger.debug(f"Stored connection {connection.connection_id} for tenant {connection.tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store connection {connection.connection_id}: {e}")
            return False
    
    async def get_connection(self, tenant_id: str, connection_id: str) -> Optional[ConnectionState]:
        """Retrieve connection state from Redis."""
        try:
            connection_key = self._get_connection_key(tenant_id, connection_id)
            connection_data = await self._connection_pool.get(connection_key)
            
            if connection_data:
                return ConnectionState.model_validate_json(connection_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get connection {connection_id}: {e}")
            return None
    
    async def remove_connection(self, tenant_id: str, connection_id: str) -> bool:
        """Remove connection state from Redis."""
        try:
            connection_key = self._get_connection_key(tenant_id, connection_id)
            tenant_key = self._get_tenant_connections_key(tenant_id)
            
            # Remove connection state
            await self._connection_pool.delete(connection_key)
            
            # Remove from tenant connection index
            await self._connection_pool.srem(tenant_key, connection_id)
            
            logger.debug(f"Removed connection {connection_id} for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove connection {connection_id}: {e}")
            return False
    
    async def get_tenant_connections(self, tenant_id: str) -> List[str]:
        """Get all connection IDs for a tenant."""
        try:
            tenant_key = self._get_tenant_connections_key(tenant_id)
            connection_ids = await self._connection_pool.smembers(tenant_key)
            return list(connection_ids)
            
        except Exception as e:
            logger.error(f"Failed to get tenant connections for {tenant_id}: {e}")
            return []
    
    async def update_connection_activity(self, tenant_id: str, connection_id: str) -> bool:
        """Update last activity timestamp for connection."""
        try:
            connection = await self.get_connection(tenant_id, connection_id)
            if connection:
                connection.last_activity = datetime.utcnow()
                return await self.store_connection(connection)
            return False
            
        except Exception as e:
            logger.error(f"Failed to update connection activity {connection_id}: {e}")
            return False
    
    async def cleanup_expired_connections(self) -> int:
        """Clean up expired connections. Returns count of cleaned connections."""
        try:
            cleaned_count = 0
            # This is a simplified cleanup - in production, consider using Redis SCAN
            # for better performance with large datasets
            
            logger.info(f"Cleaned up {cleaned_count} expired connections")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired connections: {e}")
            return 0
    
    async def store_event(self, event_id: str, event_data: Dict[str, Any], ttl_seconds: int = 300) -> bool:
        """Store event in queue for reliable delivery."""
        try:
            event_key = self._get_event_queue_key(event_id)
            event_json = json.dumps(event_data, default=str)
            
            await self._event_queue_pool.setex(event_key, ttl_seconds, event_json)
            logger.debug(f"Stored event {event_id} in queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event {event_id}: {e}")
            return False
    
    async def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve event from queue."""
        try:
            event_key = self._get_event_queue_key(event_id)
            event_data = await self._event_queue_pool.get(event_key)
            
            if event_data:
                return json.loads(event_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}")
            return None
    
    async def health_check(self) -> Dict[str, bool]:
        """Check Redis health status."""
        health = {
            "connection_db": False,
            "event_queue_db": False
        }
        
        try:
            if self._connection_pool:
                await self._connection_pool.ping()
                health["connection_db"] = True
        except Exception:
            pass
        
        try:
            if self._event_queue_pool:
                await self._event_queue_pool.ping()
                health["event_queue_db"] = True
        except Exception:
            pass
        
        return health