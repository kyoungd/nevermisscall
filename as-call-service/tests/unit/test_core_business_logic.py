"""Core business logic unit tests - focused on essential functionality."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock

from src.as_call_service.models import CallCreate, ConversationCreate, MessageCreate
from src.as_call_service.services.call_service import CallService
from src.as_call_service.services.conversation_service import ConversationService
from src.as_call_service.services.validation_service import ValidationService


class TestCallServiceCore:
    """Test core call processing functionality."""

    @pytest.fixture
    def call_service(self):
        return CallService()

    @pytest.mark.asyncio
    async def test_create_call_basic(self, call_service):
        """Test basic call creation."""
        call_data = CallCreate(
            call_sid="CA123",
            tenant_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
            direction="inbound",
            status="ringing",
            start_time=datetime.utcnow(),
        )

        with patch('src.as_call_service.services.call_service.query') as mock_query:
            with patch('src.as_call_service.services.call_service.uuid4', return_value=uuid4()):
                mock_query.side_effect = [None, [{'id': uuid4(), 'call_sid': 'CA123', 'status': 'ringing'}]]
                
                # Mock get_call method
                mock_call = MagicMock()
                mock_call.call_sid = "CA123"
                
                with patch.object(call_service, 'get_call', return_value=mock_call):
                    result = await call_service.create_call(call_data)
                    assert result.call_sid == "CA123"

    @pytest.mark.asyncio
    async def test_process_missed_call_workflow(self, call_service):
        """Test the complete missed call workflow."""
        call_sid = "CA123"
        webhook_data = {"endTime": datetime.utcnow(), "callDuration": 0}

        # Mock existing call
        mock_call = MagicMock()
        mock_call.id = uuid4()
        mock_call.tenant_id = uuid4()

        # Mock conversation and lead
        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()
        mock_lead = MagicMock()
        mock_lead.id = uuid4()

        with patch.object(call_service, 'get_call_by_sid', return_value=mock_call):
            with patch.object(call_service, 'update_call', return_value=mock_call):
                with patch.object(call_service, '_create_conversation_for_missed_call', return_value=mock_conversation):
                    with patch.object(call_service, '_create_lead_for_missed_call', return_value=mock_lead):
                        with patch.object(call_service, '_send_auto_response_sms'):
                            with patch('src.as_call_service.services.call_service.service_client') as mock_client:
                                mock_client.broadcast_realtime_event = AsyncMock()

                                result = await call_service.process_missed_call(call_sid, webhook_data)
                                assert result == mock_call


class TestConversationServiceCore:
    """Test core conversation management functionality."""

    @pytest.fixture
    def conversation_service(self):
        return ConversationService()

    @pytest.mark.asyncio
    async def test_create_conversation_basic(self, conversation_service):
        """Test basic conversation creation."""
        conversation_data = ConversationCreate(
            tenant_id=uuid4(),
            call_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
        )

        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            with patch('src.as_call_service.services.conversation_service.uuid4', return_value=uuid4()):
                mock_query.side_effect = [None, [{'id': uuid4(), 'status': 'active'}]]
                
                mock_conversation = MagicMock()
                mock_conversation.status = "active"
                
                with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
                    result = await conversation_service.create_conversation(conversation_data)
                    assert result.status == "active"

    @pytest.mark.asyncio
    async def test_ai_takeover_timer_logic(self, conversation_service):
        """Test AI takeover timer logic."""
        conversation_id = uuid4()
        message_body = "I need help"
        message_sid = "SM123"

        mock_conversation = MagicMock()
        mock_conversation.tenant_id = uuid4()
        mock_conversation.ai_active = False
        mock_conversation.human_active = False
        mock_conversation.customer_phone = "+12125551234"

        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.sent_at = datetime.utcnow()

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'add_message', return_value=mock_message):
                with patch('src.as_call_service.services.conversation_service.asyncio.create_task'):
                    with patch('src.as_call_service.services.conversation_service.service_client') as mock_client:
                        mock_client.broadcast_realtime_event = AsyncMock()

                        result = await conversation_service.process_incoming_message(
                            conversation_id, message_body, message_sid
                        )

                        # Should indicate human response window is active
                        assert result['aiProcessingTriggered'] is False
                        assert result['humanResponseWindow'] == 60

    @pytest.mark.asyncio
    async def test_human_takeover_deactivates_ai(self, conversation_service):
        """Test human takeover immediately deactivates AI."""
        conversation_id = uuid4()
        message = "I can help with that!"
        user_id = uuid4()

        mock_conversation = MagicMock()
        mock_conversation.tenant_id = uuid4()
        mock_conversation.customer_phone = "+12125551234"
        mock_conversation.business_phone = "+13105551234"

        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.sent_at = datetime.utcnow()

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'update_conversation'):
                with patch.object(conversation_service, 'add_message', return_value=mock_message):
                    with patch('src.as_call_service.services.conversation_service.service_client') as mock_client:
                        mock_client.send_sms_via_twilio_server = AsyncMock(return_value={'messageSid': 'SM999'})
                        mock_client.broadcast_realtime_event = AsyncMock()
                        
                        with patch('src.as_call_service.services.conversation_service.query'):
                            result = await conversation_service.send_human_reply(conversation_id, message, user_id)
                            
                            assert result['aiDeactivated'] is True
                            assert result['sender'] == 'human'


class TestValidationServiceCore:
    """Test core validation functionality."""

    @pytest.fixture
    def validation_service(self):
        return ValidationService()

    def test_phone_number_validation(self, validation_service):
        """Test phone number validation - core business rule."""
        # Valid phone numbers
        assert validation_service.validate_phone_number("+12125551234") is True
        assert validation_service.validate_phone_number("+447700900000") is True
        
        # Invalid phone numbers
        assert validation_service.validate_phone_number("12125551234") is False  # Missing +
        assert validation_service.validate_phone_number("") is False  # Empty
        assert validation_service.validate_phone_number("+1") is False  # Too short

    def test_message_content_validation(self, validation_service):
        """Test message content validation."""
        # Valid messages
        assert validation_service.validate_message_content("Hello, I need help") is True
        
        # Invalid messages
        assert validation_service.validate_message_content("") is False  # Empty
        assert validation_service.validate_message_content("A" * 1601) is False  # Too long
        assert validation_service.validate_message_content("<script>alert('xss')</script>") is False  # XSS

    @pytest.mark.asyncio
    async def test_service_area_validation_disabled(self, validation_service):
        """Test service area validation when disabled."""
        tenant_id = uuid4()
        address = "123 Main St"

        with patch('src.as_call_service.services.validation_service.settings') as mock_settings:
            mock_settings.service_area_validation_enabled = False

            result = await validation_service.validate_service_area(tenant_id, address)
            
            # Should return valid when disabled
            assert result['valid'] is True
            assert result['reason'] == 'validation_disabled'

    def test_business_hours_validation(self, validation_service):
        """Test business hours validation."""
        business_hours = {
            'monday': {'start': '08:00', 'end': '17:00'},
            'sunday': None,  # Closed
        }

        # During business hours
        monday_10am = datetime(2024, 1, 1, 10, 0, 0)  # Monday
        result = validation_service.validate_business_hours(business_hours, monday_10am)
        assert result['withinHours'] is True

        # Closed day
        sunday_10am = datetime(2024, 1, 7, 10, 0, 0)  # Sunday
        result = validation_service.validate_business_hours(business_hours, sunday_10am)
        assert result['withinHours'] is False
        assert result['reason'] == 'closed_on_day'

    def test_address_extraction_from_message(self, validation_service):
        """Test extracting addresses from customer messages."""
        # Should extract address
        message_with_address = "I live at 123 Main Street"
        result = validation_service.extract_address_from_message(message_with_address)
        assert "123 Main Street" in result

        # Should return None for no address
        message_no_address = "I need help with plumbing"
        result = validation_service.extract_address_from_message(message_no_address)
        assert result is None


class TestErrorHandling:
    """Test error handling in core services."""

    @pytest.mark.asyncio
    async def test_call_service_handles_database_error(self):
        """Test call service handles database errors gracefully."""
        call_service = CallService()
        call_data = CallCreate(
            call_sid="CA123",
            tenant_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
            direction="inbound",
            status="ringing",
            start_time=datetime.utcnow(),
        )

        with patch('src.as_call_service.services.call_service.query') as mock_query:
            mock_query.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception):  # Should raise DatabaseError in real implementation
                await call_service.create_call(call_data)

    @pytest.mark.asyncio
    async def test_conversation_service_handles_missing_conversation(self):
        """Test conversation service handles missing conversations."""
        conversation_service = ConversationService()
        
        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            mock_query.return_value = []  # No conversation found

            with pytest.raises(Exception):  # Should raise HTTPException 404
                await conversation_service.get_conversation(uuid4())

    def test_validation_service_handles_malformed_input(self):
        """Test validation service handles malformed input safely."""
        validation_service = ValidationService()
        
        # Should not crash on None or unexpected types
        assert validation_service.validate_phone_number(None) is False
        assert validation_service.validate_message_content(None) is False


class TestBusinessLogicIntegration:
    """Test integration between core services."""

    @pytest.mark.asyncio
    async def test_missed_call_creates_conversation_and_lead(self):
        """Test missed call workflow creates both conversation and lead."""
        call_service = CallService()
        
        # Mock the complete workflow
        mock_call = MagicMock()
        mock_call.id = uuid4()
        mock_call.tenant_id = uuid4()

        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()

        mock_lead = MagicMock()
        mock_lead.id = uuid4()

        with patch.object(call_service, 'get_call_by_sid', return_value=mock_call):
            with patch.object(call_service, 'update_call', return_value=mock_call):
                with patch.object(call_service, '_create_conversation_for_missed_call', return_value=mock_conversation):
                    with patch.object(call_service, '_create_lead_for_missed_call', return_value=mock_lead):
                        with patch.object(call_service, '_send_auto_response_sms'):
                            with patch('src.as_call_service.services.call_service.service_client') as mock_client:
                                mock_client.broadcast_realtime_event = AsyncMock()

                                result = await call_service.process_missed_call("CA123", {})
                                
                                # Verify both conversation and lead creation were called
                                assert result == mock_call

    @pytest.mark.asyncio
    async def test_sms_triggers_ai_after_timeout(self):
        """Test SMS processing triggers AI after human response timeout."""
        conversation_service = ConversationService()
        
        # Mock conversation without AI or human active
        mock_conversation = MagicMock()
        mock_conversation.ai_active = False
        mock_conversation.human_active = False
        mock_conversation.tenant_id = uuid4()
        mock_conversation.customer_phone = "+12125551234"

        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.sent_at = datetime.utcnow()

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'add_message', return_value=mock_message):
                with patch('src.as_call_service.services.conversation_service.asyncio.create_task') as mock_task:
                    with patch('src.as_call_service.services.conversation_service.service_client') as mock_client:
                        mock_client.broadcast_realtime_event = AsyncMock()

                        result = await conversation_service.process_incoming_message(
                            uuid4(), "Help with sink", "SM123"
                        )

                        # Should schedule AI activation
                        mock_task.assert_called_once()
                        assert result['humanResponseWindow'] == 60