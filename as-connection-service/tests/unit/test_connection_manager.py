"""Test connection manager."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.as_connection_service.services.connection_manager import ConnectionManager
from src.as_connection_service.models.connection import ConnectionState


class TestConnectionManager:
    """Test ConnectionManager class."""
    
    @pytest.mark.asyncio
    async def test_successful_connection(
        self, 
        connection_manager, 
        sample_auth_data, 
        sample_environ,
        mock_redis_client,
        mock_socketio_server
    ):
        """Test successful WebSocket connection."""
        # Setup mocks
        mock_redis_client.store_connection.return_value = True
        mock_redis_client.get_tenant_connections.return_value = []  # No existing connections
        
        # Test connection
        result = await connection_manager.handle_connection(
            "test-socket-id",
            sample_environ,
            sample_auth_data
        )
        
        assert result is True
        
        # Verify Redis calls
        mock_redis_client.store_connection.assert_called_once()
        
        # Verify Socket.IO calls
        mock_socketio_server.enter_room.assert_called()
        mock_socketio_server.emit.assert_called_with(
            'authenticated',
            {
                'userId': 'test-user-id',
                'tenantId': 'test-tenant-id',
                'connectionId': pytest.any,
                'serverTime': pytest.any
            },
            room='test-socket-id'
        )
    
    @pytest.mark.asyncio
    async def test_connection_without_auth(
        self,
        connection_manager,
        sample_environ,
        mock_socketio_server
    ):
        """Test connection without authentication."""
        result = await connection_manager.handle_connection(
            "test-socket-id",
            sample_environ,
            None  # No auth
        )
        
        assert result is False
        
        # Should emit error
        mock_socketio_server.emit.assert_called_with(
            'error',
            {
                'code': 'AUTHENTICATION_FAILED',
                'message': 'Authentication token required',
                'timestamp': pytest.any
            },
            room='test-socket-id'
        )
    
    @pytest.mark.asyncio
    async def test_connection_with_invalid_token(
        self,
        connection_manager,
        sample_auth_data,
        sample_environ,
        mock_auth_service,
        mock_socketio_server
    ):
        """Test connection with invalid token."""
        # Mock invalid authentication
        mock_auth_service.authenticate_socket_connection.return_value = None
        
        result = await connection_manager.handle_connection(
            "test-socket-id",
            sample_environ,
            sample_auth_data
        )
        
        assert result is False
        
        # Should emit authentication error
        mock_socketio_server.emit.assert_called_with(
            'error',
            {
                'code': 'AUTHENTICATION_FAILED',
                'message': 'Invalid or expired token',
                'timestamp': pytest.any
            },
            room='test-socket-id'
        )
    
    @pytest.mark.asyncio
    async def test_connection_limit_exceeded(
        self,
        connection_manager,
        sample_auth_data,
        sample_environ,
        mock_redis_client,
        mock_socketio_server
    ):
        """Test connection when limit is exceeded."""
        # Mock connection limit exceeded
        mock_redis_client.get_tenant_connections.return_value = [
            f"conn-{i}" for i in range(15)  # More than max (10)
        ]
        
        result = await connection_manager.handle_connection(
            "test-socket-id",
            sample_environ,
            sample_auth_data
        )
        
        assert result is False
        
        # Should emit connection limit error
        mock_socketio_server.emit.assert_called_with(
            'error',
            {
                'code': 'CONNECTION_LIMIT_EXCEEDED',
                'message': 'Too many connections for tenant',
                'timestamp': pytest.any
            },
            room='test-socket-id'
        )
    
    @pytest.mark.asyncio
    async def test_redis_storage_failure(
        self,
        connection_manager,
        sample_auth_data,
        sample_environ,
        mock_redis_client,
        mock_socketio_server
    ):
        """Test Redis storage failure during connection."""
        # Mock Redis storage failure
        mock_redis_client.get_tenant_connections.return_value = []  # Under limit
        mock_redis_client.store_connection.return_value = False  # Storage fails
        
        result = await connection_manager.handle_connection(
            "test-socket-id",
            sample_environ,
            sample_auth_data
        )
        
        assert result is False
        
        # Should emit internal error
        mock_socketio_server.emit.assert_called_with(
            'error',
            {
                'code': 'INTERNAL_ERROR',
                'message': 'Failed to establish connection',
                'timestamp': pytest.any
            },
            room='test-socket-id'
        )
    
    @pytest.mark.asyncio
    async def test_disconnection_handling(self, connection_manager):
        """Test WebSocket disconnection handling."""
        # Setup connection tracking
        connection_manager._socket_to_connection["test-socket-id"] = "test-conn-id"
        connection_manager._connection_to_socket["test-conn-id"] = "test-socket-id"
        
        # Test disconnection
        await connection_manager.handle_disconnection("test-socket-id")
        
        # Verify cleanup
        assert "test-socket-id" not in connection_manager._socket_to_connection
        assert "test-conn-id" not in connection_manager._connection_to_socket
    
    @pytest.mark.asyncio
    async def test_disconnection_unknown_socket(self, connection_manager):
        """Test disconnection for unknown socket."""
        # This should not raise an error
        await connection_manager.handle_disconnection("unknown-socket-id")
    
    @pytest.mark.asyncio
    async def test_room_name_generation(self, connection_manager):
        """Test room name generation."""
        tenant_room = connection_manager._generate_room_name('tenant', 'tenant-123')
        assert tenant_room == 'tenant:tenant-123'
        
        conversation_room = connection_manager._generate_room_name('conversation', 'conv-456')
        assert conversation_room == 'conversation:conv-456'
        
        user_room = connection_manager._generate_room_name('user', 'user-789')
        assert user_room == 'user:user-789'
    
    @pytest.mark.asyncio
    async def test_subscribe_to_conversation(
        self,
        connection_manager,
        mock_socketio_server
    ):
        """Test subscribing to conversation."""
        result = await connection_manager.subscribe_to_conversation(
            "test-socket-id",
            "conversation-123"
        )
        
        assert result is True
        mock_socketio_server.enter_room.assert_called_with(
            "test-socket-id",
            "conversation:conversation-123"
        )
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_conversation(
        self,
        connection_manager,
        mock_socketio_server
    ):
        """Test unsubscribing from conversation."""
        result = await connection_manager.unsubscribe_from_conversation(
            "test-socket-id",
            "conversation-123"
        )
        
        assert result is True
        mock_socketio_server.leave_room.assert_called_with(
            "test-socket-id",
            "conversation:conversation-123"
        )
    
    @pytest.mark.asyncio
    async def test_get_tenant_connection_count(
        self,
        connection_manager,
        mock_redis_client
    ):
        """Test getting tenant connection count."""
        mock_redis_client.get_tenant_connections.return_value = ["conn-1", "conn-2", "conn-3"]
        
        count = await connection_manager.get_tenant_connection_count("tenant-123")
        
        assert count == 3
        mock_redis_client.get_tenant_connections.assert_called_with("tenant-123")
    
    @pytest.mark.asyncio
    async def test_get_all_active_connections(self, connection_manager):
        """Test getting all active connections."""
        # Setup some connections
        connection_manager._socket_to_connection = {
            "socket-1": "conn-1",
            "socket-2": "conn-2"
        }
        
        connections = await connection_manager.get_all_active_connections()
        
        assert connections["total"] == 2