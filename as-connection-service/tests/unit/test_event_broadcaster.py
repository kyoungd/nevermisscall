"""Test event broadcaster."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from src.as_connection_service.services.event_broadcaster import EventBroadcaster


class TestEventBroadcaster:
    """Test EventBroadcaster class."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcasting event to tenant."""
        # Setup mocks
        mock_redis_client.get_tenant_connections.return_value = ["conn-1", "conn-2"]
        mock_redis_client.store_event.return_value = True
        
        result = await event_broadcaster.broadcast_to_tenant(
            "tenant-123",
            "call_incoming",
            {"callId": "call-456", "phone": "+1234567890"}
        )
        
        assert result["success"] is True
        assert result["broadcast"]["event"] == "call_incoming"
        assert result["broadcast"]["tenant_id"] == "tenant-123"
        assert result["broadcast"]["connections_sent"] == 2
        
        # Verify Socket.IO emit
        mock_socketio_server.emit.assert_called_with(
            "call_incoming",
            {
                "event": "call_incoming",
                "data": {"callId": "call-456", "phone": "+1234567890"},
                "timestamp": pytest.any
            },
            room="tenant:tenant-123"
        )
        
        # Verify event storage
        mock_redis_client.store_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_to_conversation(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcasting event to conversation."""
        mock_redis_client.store_event.return_value = True
        
        result = await event_broadcaster.broadcast_to_conversation(
            "conversation-123",
            "message_received",
            {"messageId": "msg-456", "body": "Hello"}
        )
        
        assert result["success"] is True
        assert result["broadcast"]["event"] == "message_received"
        assert result["broadcast"]["conversation_id"] == "conversation-123"
        
        # Verify Socket.IO emit
        mock_socketio_server.emit.assert_called_with(
            "message_received",
            {
                "event": "message_received",
                "data": {"messageId": "msg-456", "body": "Hello"},
                "timestamp": pytest.any
            },
            room="conversation:conversation-123"
        )
    
    @pytest.mark.asyncio
    async def test_broadcast_call_incoming(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcasting call incoming event."""
        mock_redis_client.get_tenant_connections.return_value = ["conn-1"]
        mock_redis_client.store_event.return_value = True
        
        call_data = {
            "callId": "call-123",
            "callSid": "CA1234567890abcdef",
            "customerPhone": "+12125551234",
            "status": "ringing"
        }
        
        result = await event_broadcaster.broadcast_call_incoming("tenant-123", call_data)
        
        assert result["success"] is True
        mock_socketio_server.emit.assert_called_with(
            "call_incoming",
            {
                "event": "call_incoming", 
                "data": call_data,
                "timestamp": pytest.any
            },
            room="tenant:tenant-123"
        )
    
    @pytest.mark.asyncio
    async def test_broadcast_call_missed(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcasting call missed event."""
        mock_redis_client.get_tenant_connections.return_value = ["conn-1"]
        mock_redis_client.store_event.return_value = True
        
        call_data = {
            "callId": "call-123",
            "customerPhone": "+12125551234",
            "conversationId": "conversation-456",
            "autoResponseSent": True
        }
        
        result = await event_broadcaster.broadcast_call_missed("tenant-123", call_data)
        
        assert result["success"] is True
        mock_socketio_server.emit.assert_called_with(
            "call_missed",
            {
                "event": "call_missed",
                "data": call_data,
                "timestamp": pytest.any
            },
            room="tenant:tenant-123"
        )
    
    @pytest.mark.asyncio
    async def test_broadcast_message_received(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcasting message received event."""
        mock_redis_client.get_tenant_connections.return_value = ["conn-1"]
        mock_redis_client.store_event.return_value = True
        
        message_data = {
            "conversationId": "conversation-123",
            "messageId": "message-456",
            "body": "I need help with plumbing",
            "aiResponsePending": True
        }
        
        result = await event_broadcaster.broadcast_message_received(
            "tenant-123",
            "conversation-123",
            message_data
        )
        
        assert result["success"] is True
        assert result["tenant_broadcast"]["success"] is True
        assert result["conversation_broadcast"]["success"] is True
        
        # Should call emit twice (tenant and conversation rooms)
        assert mock_socketio_server.emit.call_count == 2
    
    @pytest.mark.asyncio
    async def test_broadcast_ai_activated(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcasting AI activation event."""
        mock_redis_client.get_tenant_connections.return_value = ["conn-1"]
        mock_redis_client.store_event.return_value = True
        
        activation_data = {
            "conversationId": "conversation-123",
            "customerPhone": "+12125551234",
            "reason": "human_response_timeout"
        }
        
        result = await event_broadcaster.broadcast_ai_activated(
            "tenant-123",
            "conversation-123",
            activation_data
        )
        
        assert result["success"] is True
        assert mock_socketio_server.emit.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_takeover_confirmation(
        self,
        event_broadcaster,
        mock_socketio_server
    ):
        """Test sending takeover confirmation."""
        confirmation_data = {
            "conversationId": "conversation-123",
            "aiDeactivated": True,
            "messageId": "message-456"
        }
        
        result = await event_broadcaster.send_takeover_confirmation(
            "socket-123",
            "conversation-123",
            confirmation_data
        )
        
        assert result is True
        mock_socketio_server.emit.assert_called_with(
            "takeover_confirmed",
            {
                "event": "takeover_confirmed",
                "data": confirmation_data,
                "timestamp": pytest.any
            },
            room="socket-123"
        )
    
    @pytest.mark.asyncio
    async def test_send_message_confirmation(
        self,
        event_broadcaster,
        mock_socketio_server
    ):
        """Test sending message confirmation."""
        confirmation_data = {
            "conversationId": "conversation-123",
            "messageId": "message-456",
            "status": "sent"
        }
        
        result = await event_broadcaster.send_message_confirmation(
            "socket-123",
            "conversation-123",
            confirmation_data
        )
        
        assert result is True
        mock_socketio_server.emit.assert_called_with(
            "message_sent_confirmation",
            {
                "event": "message_sent_confirmation",
                "data": confirmation_data,
                "timestamp": pytest.any
            },
            room="socket-123"
        )
    
    @pytest.mark.asyncio
    async def test_send_error(
        self,
        event_broadcaster,
        mock_socketio_server
    ):
        """Test sending error message."""
        result = await event_broadcaster.send_error(
            "socket-123",
            "INVALID_REQUEST",
            "Missing required field"
        )
        
        assert result is True
        mock_socketio_server.emit.assert_called_with(
            "error",
            {
                "event": "error",
                "data": {
                    "code": "INVALID_REQUEST",
                    "message": "Missing required field",
                    "timestamp": pytest.any
                }
            },
            room="socket-123"
        )
    
    @pytest.mark.asyncio
    async def test_broadcast_failure(
        self,
        event_broadcaster,
        mock_socketio_server,
        mock_redis_client
    ):
        """Test broadcast failure handling."""
        # Mock Socket.IO emit failure
        mock_socketio_server.emit.side_effect = Exception("Socket.IO error")
        mock_redis_client.get_tenant_connections.return_value = ["conn-1"]
        
        result = await event_broadcaster.broadcast_to_tenant(
            "tenant-123",
            "test_event",
            {"test": "data"}
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_room_name_generation(self, event_broadcaster):
        """Test room name generation."""
        tenant_room = event_broadcaster._generate_room_name('tenant', 'tenant-123')
        assert tenant_room == 'tenant:tenant-123'
        
        conversation_room = event_broadcaster._generate_room_name('conversation', 'conv-456')
        assert conversation_room == 'conversation:conv-456'
        
        user_room = event_broadcaster._generate_room_name('user', 'user-789')
        assert user_room == 'user:user-789'
        
        # Test unknown room type
        unknown_room = event_broadcaster._generate_room_name('unknown', 'id-123')
        assert unknown_room == 'unknown:id-123'