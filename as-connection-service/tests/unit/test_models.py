"""Test data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.as_connection_service.models.connection import ConnectionState, EventQueueItem
from src.as_connection_service.models.events import (
    WebSocketEvent,
    BroadcastRequest,
    AuthenticationData,
    TakeoverConversationData,
    SendMessageData,
    UpdateLeadStatusData
)


class TestConnectionState:
    """Test ConnectionState model."""
    
    def test_valid_connection_state(self):
        """Test creating valid connection state."""
        now = datetime.utcnow()
        
        connection = ConnectionState(
            connection_id="conn-123",
            socket_id="socket-456",
            user_id="user-789",
            tenant_id="tenant-001",
            connected_at=now,
            last_activity=now,
            subscribed_conversations=["conv-1", "conv-2"],
            subscribed_events=["call_incoming", "message_received"],
            is_active=True,
            redis_key="connections:tenant-001:conn-123",
            ttl=3600,
            user_agent="Test Browser",
            ip_address="192.168.1.1"
        )
        
        assert connection.connection_id == "conn-123"
        assert connection.socket_id == "socket-456"
        assert connection.user_id == "user-789"
        assert connection.tenant_id == "tenant-001"
        assert connection.is_active is True
        assert len(connection.subscribed_conversations) == 2
        assert len(connection.subscribed_events) == 2
        assert connection.user_agent == "Test Browser"
        assert connection.ip_address == "192.168.1.1"
    
    def test_connection_state_without_optional_fields(self):
        """Test connection state without optional fields."""
        now = datetime.utcnow()
        
        connection = ConnectionState(
            connection_id="conn-123",
            socket_id="socket-456",
            user_id="user-789",
            tenant_id="tenant-001",
            connected_at=now,
            last_activity=now,
            subscribed_conversations=[],
            subscribed_events=[],
            is_active=True,
            redis_key="connections:tenant-001:conn-123",
            ttl=3600
        )
        
        assert connection.user_agent is None
        assert connection.ip_address is None
    
    def test_connection_state_validation_error(self):
        """Test connection state validation errors."""
        with pytest.raises(ValidationError):
            ConnectionState()  # Missing required fields


class TestEventQueueItem:
    """Test EventQueueItem model."""
    
    def test_valid_event_queue_item(self):
        """Test creating valid event queue item."""
        now = datetime.utcnow()
        
        event = EventQueueItem(
            id="event-123",
            event="call_incoming",
            tenant_id="tenant-001",
            data={"callId": "call-456", "phone": "+1234567890"},
            target_connections=["conn-1", "conn-2"],
            delivered_connections=["conn-1"],
            failed_connections=[],
            created_at=now,
            expires_at=now,
            retry_count=0,
            max_retries=3,
            conversation_id="conv-789"
        )
        
        assert event.id == "event-123"
        assert event.event == "call_incoming"
        assert event.tenant_id == "tenant-001"
        assert event.data["callId"] == "call-456"
        assert len(event.target_connections) == 2
        assert len(event.delivered_connections) == 1
        assert event.retry_count == 0
        assert event.conversation_id == "conv-789"


class TestWebSocketEvent:
    """Test WebSocketEvent model."""
    
    def test_websocket_event_with_timestamp(self):
        """Test WebSocket event with explicit timestamp."""
        timestamp = datetime.utcnow()
        
        event = WebSocketEvent(
            event="message_received",
            data={"message": "Hello World"},
            timestamp=timestamp
        )
        
        assert event.event == "message_received"
        assert event.data["message"] == "Hello World"
        assert event.timestamp == timestamp
    
    def test_websocket_event_auto_timestamp(self):
        """Test WebSocket event with automatic timestamp."""
        event = WebSocketEvent(
            event="call_missed",
            data={"callId": "call-123"}
        )
        
        assert event.event == "call_missed"
        assert event.data["callId"] == "call-123"
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)


class TestBroadcastRequest:
    """Test BroadcastRequest model."""
    
    def test_broadcast_request_with_tenant(self):
        """Test broadcast request with tenant ID."""
        request = BroadcastRequest(
            event="dashboard_update",
            data={"activeConnections": 5},
            tenant_id="tenant-001"
        )
        
        assert request.event == "dashboard_update"
        assert request.data["activeConnections"] == 5
        assert request.tenant_id == "tenant-001"
        assert request.conversation_id is None
    
    def test_broadcast_request_with_conversation(self):
        """Test broadcast request with conversation ID."""
        request = BroadcastRequest(
            event="message_sent",
            data={"messageId": "msg-123"},
            conversation_id="conv-456"
        )
        
        assert request.event == "message_sent"
        assert request.data["messageId"] == "msg-123"
        assert request.conversation_id == "conv-456"
        assert request.tenant_id is None


class TestEventDataModels:
    """Test specific event data models."""
    
    def test_authentication_data(self):
        """Test authentication data model."""
        auth_data = AuthenticationData(token="jwt-token-123")
        
        assert auth_data.token == "jwt-token-123"
    
    def test_takeover_conversation_data(self):
        """Test takeover conversation data model."""
        takeover_data = TakeoverConversationData(
            conversation_id="conv-123",
            message="I'll take over from here"
        )
        
        assert takeover_data.conversation_id == "conv-123"
        assert takeover_data.message == "I'll take over from here"
    
    def test_send_message_data(self):
        """Test send message data model."""
        message_data = SendMessageData(
            conversation_id="conv-456",
            message="Thanks for contacting us!"
        )
        
        assert message_data.conversation_id == "conv-456"
        assert message_data.message == "Thanks for contacting us!"
    
    def test_update_lead_status_data(self):
        """Test update lead status data model."""
        lead_data = UpdateLeadStatusData(
            lead_id="lead-789",
            status="qualified",
            notes="Ready to schedule appointment"
        )
        
        assert lead_data.lead_id == "lead-789"
        assert lead_data.status == "qualified"
        assert lead_data.notes == "Ready to schedule appointment"
    
    def test_update_lead_status_data_without_notes(self):
        """Test update lead status data without notes."""
        lead_data = UpdateLeadStatusData(
            lead_id="lead-789",
            status="qualified"
        )
        
        assert lead_data.lead_id == "lead-789"
        assert lead_data.status == "qualified"
        assert lead_data.notes is None