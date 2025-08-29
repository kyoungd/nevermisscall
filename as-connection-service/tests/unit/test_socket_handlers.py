"""Test Socket.IO event handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.as_connection_service.utils.socket_handlers import create_socket_handlers
from src.as_connection_service.models.events import (
    TakeoverConversationData,
    SendMessageData,
    UpdateLeadStatusData
)


class TestSocketHandlers:
    """Test Socket.IO event handlers."""
    
    @pytest.fixture
    async def mock_sio(self):
        """Mock Socket.IO server."""
        sio = AsyncMock()
        return sio
    
    @pytest.fixture
    async def mock_connection_manager(self):
        """Mock connection manager."""
        manager = AsyncMock()
        manager.handle_connection.return_value = True
        manager.handle_disconnection.return_value = None
        manager.get_connection_by_socket.return_value = MagicMock(
            tenant_id="test-tenant",
            user_id="test-user"
        )
        manager.update_connection_activity.return_value = True
        return manager
    
    @pytest.fixture 
    async def mock_event_broadcaster(self):
        """Mock event broadcaster."""
        broadcaster = AsyncMock()
        broadcaster.send_takeover_confirmation.return_value = True
        broadcaster.send_message_confirmation.return_value = True
        broadcaster.send_error.return_value = True
        broadcaster.broadcast_lead_updated.return_value = {"success": True}
        return broadcaster
    
    @pytest.fixture
    async def mock_auth_service(self):
        """Mock auth service."""
        service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_connect_handler_success(
        self,
        mock_sio,
        mock_connection_manager,
        mock_event_broadcaster,
        mock_auth_service
    ):
        """Test successful connection handler."""
        # Create handlers
        create_socket_handlers(mock_sio, mock_connection_manager, mock_event_broadcaster, mock_auth_service)
        
        # Verify connect handler was registered
        mock_sio.event.assert_called()
        
        # Get the connect handler function
        connect_calls = [call for call in mock_sio.event.call_args_list if call[0][0] == 'connect']
        assert len(connect_calls) > 0, "Connect handler should be registered"
    
    @pytest.mark.asyncio
    async def test_disconnect_handler(
        self,
        mock_sio,
        mock_connection_manager,
        mock_event_broadcaster,
        mock_auth_service
    ):
        """Test disconnect handler."""
        # Create handlers
        create_socket_handlers(mock_sio, mock_connection_manager, mock_event_broadcaster, mock_auth_service)
        
        # Verify disconnect handler was registered
        mock_sio.event.assert_called()
    
    @pytest.mark.asyncio
    async def test_takeover_conversation_data_validation(self):
        """Test takeover conversation data validation."""
        # Valid data
        valid_data = TakeoverConversationData(
            conversation_id="conv-123",
            message="I'll take over now"
        )
        assert valid_data.conversation_id == "conv-123"
        assert valid_data.message == "I'll take over now"
        
        # Invalid data should raise validation error
        with pytest.raises(Exception):
            TakeoverConversationData(conversation_id="")  # Missing message
    
    @pytest.mark.asyncio
    async def test_send_message_data_validation(self):
        """Test send message data validation."""
        # Valid data
        valid_data = SendMessageData(
            conversation_id="conv-123",
            message="Customer service response"
        )
        assert valid_data.conversation_id == "conv-123"
        assert valid_data.message == "Customer service response"
        
        # Invalid data
        with pytest.raises(Exception):
            SendMessageData(conversation_id="conv-123")  # Missing message
    
    @pytest.mark.asyncio
    async def test_update_lead_status_data_validation(self):
        """Test update lead status data validation."""
        # Valid data with notes
        valid_data = UpdateLeadStatusData(
            lead_id="lead-123",
            status="qualified",
            notes="Ready for appointment"
        )
        assert valid_data.lead_id == "lead-123"
        assert valid_data.status == "qualified"
        assert valid_data.notes == "Ready for appointment"
        
        # Valid data without notes
        valid_data_no_notes = UpdateLeadStatusData(
            lead_id="lead-123",
            status="qualified"
        )
        assert valid_data_no_notes.notes is None
    
    @pytest.mark.asyncio
    async def test_event_handlers_registration(
        self,
        mock_sio,
        mock_connection_manager,
        mock_event_broadcaster,
        mock_auth_service
    ):
        """Test that all required event handlers are registered."""
        # Create handlers
        sio = create_socket_handlers(mock_sio, mock_connection_manager, mock_event_broadcaster, mock_auth_service)
        
        # Verify the function returns the sio instance
        assert sio == mock_sio
        
        # Verify event decorator was called multiple times
        assert mock_sio.event.call_count >= 5  # At least connect, disconnect, takeover, send_message, update_lead
    
    def test_socket_handlers_core_functionality(self):
        """Test that socket handlers module provides required functions."""
        from src.as_connection_service.utils.socket_handlers import create_socket_handlers
        
        # Verify the main function exists and is callable
        assert callable(create_socket_handlers)
        
        # Basic smoke test - function should not crash when called with mocks
        mock_sio = MagicMock()
        mock_connection_manager = MagicMock()
        mock_event_broadcaster = MagicMock()
        mock_auth_service = MagicMock()
        
        result = create_socket_handlers(mock_sio, mock_connection_manager, mock_event_broadcaster, mock_auth_service)
        assert result == mock_sio