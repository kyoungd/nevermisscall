"""Test Redis client service."""

import pytest
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.as_connection_service.services.redis_client import RedisClient
from src.as_connection_service.models.connection import ConnectionState


class TestRedisClient:
    """Test RedisClient class."""
    
    @pytest.fixture
    async def redis_client(self):
        """Create Redis client instance."""
        return RedisClient()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, redis_client):
        """Test successful Redis initialization."""
        with patch('src.as_connection_service.services.redis_client.aioredis.from_url') as mock_from_url:
            # Mock connection pools
            mock_conn_pool = AsyncMock()
            mock_event_pool = AsyncMock()
            mock_conn_pool.ping.return_value = None
            mock_event_pool.ping.return_value = None
            
            mock_from_url.side_effect = [mock_conn_pool, mock_event_pool]
            
            await redis_client.initialize()
            
            assert redis_client._connection_pool == mock_conn_pool
            assert redis_client._event_queue_pool == mock_event_pool
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, redis_client):
        """Test Redis initialization failure."""
        with patch('src.as_connection_service.services.redis_client.aioredis.from_url') as mock_from_url:
            mock_from_url.side_effect = Exception("Redis connection failed")
            
            with pytest.raises(Exception, match="Redis connection failed"):
                await redis_client.initialize()
    
    @pytest.mark.asyncio
    async def test_store_connection_success(self, redis_client, sample_connection_state):
        """Test successful connection storage."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.store_connection(sample_connection_state)
        
        assert result is True
        mock_conn_pool.setex.assert_called_once()
        mock_conn_pool.sadd.assert_called_once()
        mock_conn_pool.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_connection_failure(self, redis_client, sample_connection_state):
        """Test connection storage failure."""
        # Mock Redis pools with failure
        mock_conn_pool = AsyncMock()
        mock_conn_pool.setex.side_effect = Exception("Redis error")
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.store_connection(sample_connection_state)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_connection_success(self, redis_client):
        """Test successful connection retrieval."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        sample_data = {
            "connection_id": "test-conn-id",
            "socket_id": "test-socket-id",
            "user_id": "test-user-id",
            "tenant_id": "test-tenant-id",
            "connected_at": "2024-01-01T10:00:00",
            "last_activity": "2024-01-01T10:00:00",
            "subscribed_conversations": [],
            "subscribed_events": [],
            "is_active": True,
            "redis_key": "connections:test-tenant-id:test-conn-id",
            "ttl": 3600
        }
        mock_conn_pool.get.return_value = json.dumps(sample_data)
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.get_connection("test-tenant-id", "test-conn-id")
        
        assert result is not None
        assert result.connection_id == "test-conn-id"
        assert result.user_id == "test-user-id"
        assert result.tenant_id == "test-tenant-id"
    
    @pytest.mark.asyncio
    async def test_get_connection_not_found(self, redis_client):
        """Test connection retrieval when not found."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        mock_conn_pool.get.return_value = None
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.get_connection("test-tenant-id", "nonexistent-conn-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_connection_error(self, redis_client):
        """Test connection retrieval with error."""
        # Mock Redis pools with error
        mock_conn_pool = AsyncMock()
        mock_conn_pool.get.side_effect = Exception("Redis error")
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.get_connection("test-tenant-id", "test-conn-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_remove_connection_success(self, redis_client):
        """Test successful connection removal."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.remove_connection("test-tenant-id", "test-conn-id")
        
        assert result is True
        mock_conn_pool.delete.assert_called_once()
        mock_conn_pool.srem.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_tenant_connections_success(self, redis_client):
        """Test successful tenant connections retrieval."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        mock_conn_pool.smembers.return_value = {"conn-1", "conn-2", "conn-3"}
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.get_tenant_connections("test-tenant-id")
        
        assert len(result) == 3
        assert "conn-1" in result
        assert "conn-2" in result
        assert "conn-3" in result
    
    @pytest.mark.asyncio
    async def test_get_tenant_connections_error(self, redis_client):
        """Test tenant connections retrieval with error."""
        # Mock Redis pools with error
        mock_conn_pool = AsyncMock()
        mock_conn_pool.smembers.side_effect = Exception("Redis error")
        redis_client._connection_pool = mock_conn_pool
        
        result = await redis_client.get_tenant_connections("test-tenant-id")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_update_connection_activity_success(self, redis_client, sample_connection_state):
        """Test successful connection activity update."""
        # Mock get_connection and store_connection
        with patch.object(redis_client, 'get_connection', return_value=sample_connection_state):
            with patch.object(redis_client, 'store_connection', return_value=True):
                result = await redis_client.update_connection_activity("test-tenant-id", "test-conn-id")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_connection_activity_not_found(self, redis_client):
        """Test connection activity update when connection not found."""
        with patch.object(redis_client, 'get_connection', return_value=None):
            result = await redis_client.update_connection_activity("test-tenant-id", "nonexistent-conn-id")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_store_event_success(self, redis_client):
        """Test successful event storage."""
        # Mock Redis pools
        mock_event_pool = AsyncMock()
        redis_client._event_queue_pool = mock_event_pool
        
        event_data = {"event": "test_event", "data": {"test": "value"}}
        result = await redis_client.store_event("event-123", event_data)
        
        assert result is True
        mock_event_pool.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_event_success(self, redis_client):
        """Test successful event retrieval."""
        # Mock Redis pools
        mock_event_pool = AsyncMock()
        event_data = {"event": "test_event", "data": {"test": "value"}}
        mock_event_pool.get.return_value = json.dumps(event_data)
        redis_client._event_queue_pool = mock_event_pool
        
        result = await redis_client.get_event("event-123")
        
        assert result is not None
        assert result["event"] == "test_event"
        assert result["data"]["test"] == "value"
    
    @pytest.mark.asyncio
    async def test_get_event_not_found(self, redis_client):
        """Test event retrieval when not found."""
        # Mock Redis pools
        mock_event_pool = AsyncMock()
        mock_event_pool.get.return_value = None
        redis_client._event_queue_pool = mock_event_pool
        
        result = await redis_client.get_event("nonexistent-event-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, redis_client):
        """Test health check when all services are healthy."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        mock_event_pool = AsyncMock()
        mock_conn_pool.ping.return_value = None
        mock_event_pool.ping.return_value = None
        redis_client._connection_pool = mock_conn_pool
        redis_client._event_queue_pool = mock_event_pool
        
        result = await redis_client.health_check()
        
        assert result["connection_db"] is True
        assert result["event_queue_db"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, redis_client):
        """Test health check when services are unhealthy."""
        # Mock Redis pools with errors
        mock_conn_pool = AsyncMock()
        mock_event_pool = AsyncMock()
        mock_conn_pool.ping.side_effect = Exception("Connection failed")
        mock_event_pool.ping.side_effect = Exception("Event queue failed")
        redis_client._connection_pool = mock_conn_pool
        redis_client._event_queue_pool = mock_event_pool
        
        result = await redis_client.health_check()
        
        assert result["connection_db"] is False
        assert result["event_queue_db"] is False
    
    def test_key_generation(self, redis_client):
        """Test Redis key generation methods."""
        conn_key = redis_client._get_connection_key("tenant-123", "conn-456")
        assert conn_key == "connections:tenant-123:conn-456"
        
        tenant_key = redis_client._get_tenant_connections_key("tenant-123")
        assert tenant_key == "tenant_connections:tenant-123"
        
        event_key = redis_client._get_event_queue_key("event-789")
        assert event_key == "event_queue:event-789"
    
    @pytest.mark.asyncio
    async def test_close(self, redis_client):
        """Test closing Redis connections."""
        # Mock Redis pools
        mock_conn_pool = AsyncMock()
        mock_event_pool = AsyncMock()
        redis_client._connection_pool = mock_conn_pool
        redis_client._event_queue_pool = mock_event_pool
        
        await redis_client.close()
        
        mock_conn_pool.close.assert_called_once()
        mock_event_pool.close.assert_called_once()