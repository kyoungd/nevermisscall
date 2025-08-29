"""Test configuration and fixtures."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import socketio

from src.as_connection_service.services.redis_client import RedisClient
from src.as_connection_service.services.auth_service import AuthService
from src.as_connection_service.services.connection_manager import ConnectionManager
from src.as_connection_service.services.event_broadcaster import EventBroadcaster
from src.as_connection_service.models.connection import ConnectionState


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def mock_redis_client():
    """Mock Redis client."""
    client = AsyncMock(spec=RedisClient)
    client.initialize.return_value = None
    client.close.return_value = None
    client.health_check.return_value = {"connection_db": True, "event_queue_db": True}
    client.store_connection.return_value = True
    client.get_connection.return_value = None
    client.remove_connection.return_value = True
    client.get_tenant_connections.return_value = []
    client.update_connection_activity.return_value = True
    client.store_event.return_value = True
    client.get_event.return_value = None
    return client


@pytest.fixture
async def mock_auth_service():
    """Mock Auth service."""
    service = AsyncMock(spec=AuthService)
    service.close.return_value = None
    service.validate_jwt_token.return_value = {
        "user_id": "test-user-id",
        "tenant_id": "test-tenant-id",
        "email": "test@example.com",
        "permissions": ["read", "write"]
    }
    service.authenticate_socket_connection.return_value = {
        "user_id": "test-user-id",
        "tenant_id": "test-tenant-id",
        "email": "test@example.com",
        "permissions": ["read", "write"]
    }
    service.validate_service_key.return_value = True
    service.check_user_tenant_access.return_value = True
    return service


@pytest.fixture
async def mock_socketio_server():
    """Mock Socket.IO server."""
    sio = AsyncMock(spec=socketio.AsyncServer)
    sio.emit.return_value = None
    sio.enter_room.return_value = None
    sio.leave_room.return_value = None
    sio.disconnect.return_value = None
    return sio


@pytest.fixture
async def connection_manager(mock_socketio_server, mock_redis_client, mock_auth_service):
    """Create connection manager with mocked dependencies."""
    return ConnectionManager(mock_socketio_server, mock_redis_client, mock_auth_service)


@pytest.fixture
async def event_broadcaster(mock_socketio_server, mock_redis_client):
    """Create event broadcaster with mocked dependencies."""
    return EventBroadcaster(mock_socketio_server, mock_redis_client)


@pytest.fixture
def sample_connection_state():
    """Sample connection state for tests."""
    return ConnectionState(
        connection_id="test-conn-id",
        socket_id="test-socket-id",
        user_id="test-user-id",
        tenant_id="test-tenant-id",
        connected_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
        subscribed_conversations=[],
        subscribed_events=[],
        is_active=True,
        redis_key="connections:test-tenant-id:test-conn-id",
        ttl=3600
    )


@pytest.fixture
def sample_auth_data():
    """Sample authentication data."""
    return {
        "token": "valid-jwt-token"
    }


@pytest.fixture
def sample_environ():
    """Sample WSGI environ for connection."""
    return {
        "HTTP_USER_AGENT": "Test Browser",
        "REMOTE_ADDR": "127.0.0.1"
    }