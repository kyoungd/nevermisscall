"""Unit tests for ConversationService."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.as_call_service.models import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
)
from src.as_call_service.services.conversation_service import ConversationService
from src.as_call_service.utils import DatabaseError, ServiceError


class TestConversationService:
    """Test cases for ConversationService."""

    @pytest.fixture
    def conversation_service(self):
        """Create ConversationService instance for testing."""
        return ConversationService()

    @pytest.fixture
    def sample_conversation_create(self):
        """Sample ConversationCreate data for testing."""
        return ConversationCreate(
            tenant_id=uuid4(),
            call_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
        )

    @pytest.fixture
    def sample_message_create(self):
        """Sample MessageCreate data for testing."""
        return MessageCreate(
            conversation_id=uuid4(),
            tenant_id=uuid4(),
            direction="inbound",
            sender="customer",
            body="I need help with my plumbing",
        )

    @pytest.mark.asyncio
    async def test_create_conversation_success(self, conversation_service, sample_conversation_create):
        """Test successful conversation creation."""
        conversation_id = uuid4()
        mock_conversation_data = {
            'id': conversation_id,
            'tenant_id': sample_conversation_create.tenant_id,
            'call_id': sample_conversation_create.call_id,
            'customer_phone': sample_conversation_create.customer_phone,
            'business_phone': sample_conversation_create.business_phone,
            'status': 'active',
            'ai_active': False,
            'human_active': False,
            'ai_handoff_time': None,
            'human_takeover_time': None,
            'last_message_time': datetime.utcnow(),
            'last_human_response_time': None,
            'message_count': 0,
            'ai_message_count': 0,
            'human_message_count': 0,
            'appointment_scheduled': False,
            'outcome': None,
            'lead_id': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }

        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            with patch('src.as_call_service.services.conversation_service.uuid4', return_value=conversation_id):
                # Mock database operations
                mock_query.side_effect = [None, [mock_conversation_data]]  # insert, then select

                result = await conversation_service.create_conversation(sample_conversation_create)

                # Verify database calls
                assert mock_query.call_count == 2
                insert_call = mock_query.call_args_list[0]
                assert "INSERT INTO conversations" in insert_call[0][0]

                # Verify result
                assert result.id == conversation_id
                assert result.status == "active"

    @pytest.mark.asyncio
    async def test_create_conversation_missing_required_field(self, conversation_service):
        """Test conversation creation with missing required field."""
        invalid_conversation_data = ConversationCreate(
            tenant_id=uuid4(),
            call_id=None,  # Missing required field
            customer_phone="+12125551234",
            business_phone="+13105551234",
        )

        with pytest.raises(ValueError, match="call_id is required"):
            await conversation_service.create_conversation(invalid_conversation_data)

    @pytest.mark.asyncio
    async def test_add_message_success(self, conversation_service, sample_message_create):
        """Test successful message addition."""
        message_id = uuid4()
        mock_message_data = {
            'id': message_id,
            'conversation_id': sample_message_create.conversation_id,
            'tenant_id': sample_message_create.tenant_id,
            'direction': sample_message_create.direction,
            'sender': sample_message_create.sender,
            'body': sample_message_create.body,
            'message_sid': None,
            'processed': False,
            'ai_processed': False,
            'confidence': None,
            'intent': None,
            'status': 'sent',
            'error_code': None,
            'error_message': None,
            'sent_at': datetime.utcnow(),
            'delivered_at': None,
            'created_at': datetime.utcnow(),
        }

        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            with patch('src.as_call_service.services.conversation_service.uuid4', return_value=message_id):
                with patch.object(conversation_service, '_update_conversation_message_stats'):
                    # Mock database operations
                    mock_query.side_effect = [None, [mock_message_data]]  # insert, then select

                    result = await conversation_service.add_message(sample_message_create)

                    # Verify database calls
                    assert mock_query.call_count == 2
                    insert_call = mock_query.call_args_list[0]
                    assert "INSERT INTO messages" in insert_call[0][0]

                    # Verify result
                    assert result.id == message_id
                    assert result.body == sample_message_create.body
                    assert result.sender == "customer"

    @pytest.mark.asyncio
    async def test_get_conversation_messages_success(self, conversation_service):
        """Test getting conversation messages."""
        conversation_id = uuid4()
        mock_messages_data = [
            {
                'id': uuid4(),
                'conversation_id': conversation_id,
                'tenant_id': uuid4(),
                'direction': 'outbound',
                'sender': 'system',
                'body': 'Hi! Sorry we missed your call.',
                'message_sid': 'SM1234',
                'processed': True,
                'ai_processed': False,
                'confidence': None,
                'intent': None,
                'status': 'delivered',
                'error_code': None,
                'error_message': None,
                'sent_at': datetime.utcnow(),
                'delivered_at': datetime.utcnow(),
                'created_at': datetime.utcnow(),
            },
            {
                'id': uuid4(),
                'conversation_id': conversation_id,
                'tenant_id': uuid4(),
                'direction': 'inbound',
                'sender': 'customer',
                'body': 'I need help with my sink',
                'message_sid': 'SM5678',
                'processed': True,
                'ai_processed': False,
                'confidence': None,
                'intent': None,
                'status': 'sent',
                'error_code': None,
                'error_message': None,
                'sent_at': datetime.utcnow(),
                'delivered_at': None,
                'created_at': datetime.utcnow(),
            }
        ]

        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            mock_query.return_value = mock_messages_data

            result = await conversation_service.get_conversation_messages(conversation_id)

            # Verify query
            mock_query.assert_called_once()
            assert "WHERE conversation_id = $1" in mock_query.call_args[0][0]
            assert "ORDER BY created_at ASC" in mock_query.call_args[0][0]

            # Verify result
            assert len(result) == 2
            assert result[0].sender == "system"
            assert result[1].sender == "customer"

    @pytest.mark.asyncio
    async def test_process_incoming_message_new_conversation(self, conversation_service):
        """Test processing incoming message for conversation without AI active."""
        conversation_id = uuid4()
        message_body = "I need help with my sink"
        message_sid = "SM1234567890"

        mock_conversation = MagicMock()
        mock_conversation.tenant_id = uuid4()
        mock_conversation.ai_active = False
        mock_conversation.human_active = False
        mock_conversation.customer_phone = "+12125551234"

        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.direction = "inbound"
        mock_message.sent_at = datetime.utcnow()

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'add_message', return_value=mock_message):
                with patch.object(conversation_service, '_schedule_ai_activation') as mock_schedule:
                    with patch('src.as_call_service.services.conversation_service.service_client') as mock_client:
                        mock_client.broadcast_realtime_event = AsyncMock()

                        # Mock asyncio.create_task
                        with patch('src.as_call_service.services.conversation_service.asyncio.create_task'):
                            result = await conversation_service.process_incoming_message(
                                conversation_id, message_body, message_sid
                            )

                        # Verify result
                        assert result['aiProcessingTriggered'] is False
                        assert result['humanResponseWindow'] == 60  # Default AI takeover delay

                        # Verify real-time event was broadcast
                        mock_client.broadcast_realtime_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_incoming_message_ai_active(self, conversation_service):
        """Test processing incoming message when AI is active."""
        conversation_id = uuid4()
        message_body = "Can you come tomorrow?"
        message_sid = "SM1234567890"

        mock_conversation = MagicMock()
        mock_conversation.tenant_id = uuid4()
        mock_conversation.ai_active = True
        mock_conversation.human_active = False
        mock_conversation.customer_phone = "+12125551234"

        mock_message = MagicMock()
        mock_message.id = uuid4()
        mock_message.sent_at = datetime.utcnow()

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'add_message', return_value=mock_message):
                with patch.object(conversation_service, '_trigger_ai_processing') as mock_ai_process:
                    with patch('src.as_call_service.services.conversation_service.service_client') as mock_client:
                        mock_client.broadcast_realtime_event = AsyncMock()

                        result = await conversation_service.process_incoming_message(
                            conversation_id, message_body, message_sid
                        )

                        # Verify AI processing was triggered
                        mock_ai_process.assert_called_once_with(conversation_id, message_body)
                        assert result['aiProcessingTriggered'] is True

    @pytest.mark.asyncio
    async def test_send_human_reply_success(self, conversation_service):
        """Test successful human reply sending."""
        conversation_id = uuid4()
        message = "I can help with that! When would be a good time?"
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
                        mock_client.send_sms_via_twilio_server = AsyncMock(return_value={'messageSid': 'SM9999'})
                        mock_client.broadcast_realtime_event = AsyncMock()

                        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
                            result = await conversation_service.send_human_reply(conversation_id, message, user_id)

                            # Verify SMS was sent
                            mock_client.send_sms_via_twilio_server.assert_called_once()
                            sms_args = mock_client.send_sms_via_twilio_server.call_args[1]
                            assert sms_args['message'] == message

                            # Verify result
                            assert result['aiDeactivated'] is True
                            assert result['sender'] == 'human'

    @pytest.mark.asyncio
    async def test_get_active_conversations_for_tenant(self, conversation_service):
        """Test getting active conversations for tenant."""
        tenant_id = uuid4()
        mock_conversations_data = [
            {
                'id': uuid4(),
                'customer_phone': '+12125551234',
                'status': 'active',
                'ai_active': False,
                'human_active': True,
                'last_message_time': datetime.utcnow(),
                'message_count': 3,
                'last_message': 'I can help with that!',
                'lead_status': 'qualified',
            },
            {
                'id': uuid4(),
                'customer_phone': '+13105551234',
                'status': 'active',
                'ai_active': True,
                'human_active': False,
                'last_message_time': datetime.utcnow(),
                'message_count': 2,
                'last_message': 'Let me check my schedule',
                'lead_status': 'new',
            }
        ]

        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            mock_query.return_value = mock_conversations_data

            result = await conversation_service.get_active_conversations_for_tenant(tenant_id)

            # Verify query
            mock_query.assert_called_once()
            assert "WHERE c.tenant_id = $1" in mock_query.call_args[0][0]
            assert "c.status = 'active'" in mock_query.call_args[0][0]

            # Verify result
            assert result['totalActive'] == 2
            assert result['aiHandledCount'] == 1
            assert result['humanHandledCount'] == 1
            assert len(result['conversations']) == 2

    @pytest.mark.asyncio
    async def test_trigger_ai_processing_success(self, conversation_service):
        """Test successful AI processing trigger."""
        conversation_id = uuid4()
        message_content = "Can you come tomorrow morning?"

        mock_conversation = MagicMock()
        mock_conversation.tenant_id = uuid4()
        mock_conversation.customer_phone = "+12125551234"
        mock_conversation.business_phone = "+13105551234"

        mock_messages = [
            MagicMock(body="Hi! Sorry we missed your call."),
            MagicMock(body="I need help with my faucet."),
        ]

        mock_ai_response = {
            'aiResponse': {
                'message': 'I can schedule you for tomorrow at 9 AM. Does that work?',
                'confidence': 0.85,
                'intent': 'schedule_appointment'
            }
        }

        mock_ai_message = MagicMock()
        mock_ai_message.id = uuid4()

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'get_conversation_messages', return_value=mock_messages):
                with patch.object(conversation_service, 'add_message', return_value=mock_ai_message):
                    with patch('src.as_call_service.services.conversation_service.service_client') as mock_client:
                        mock_client.validate_tenant_and_service_area = AsyncMock(return_value={
                            'businessName': 'Test Plumbing'
                        })
                        mock_client.process_ai_conversation = AsyncMock(return_value=mock_ai_response)
                        mock_client.send_sms_via_twilio_server = AsyncMock(return_value={'messageSid': 'SM9999'})

                        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
                            await conversation_service._trigger_ai_processing(conversation_id, message_content)

                            # Verify AI service was called
                            mock_client.process_ai_conversation.assert_called_once()
                            ai_args = mock_client.process_ai_conversation.call_args[0]
                            assert ai_args[1] == message_content  # message content

                            # Verify SMS was sent
                            mock_client.send_sms_via_twilio_server.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_ai_activation_cancelled(self, conversation_service):
        """Test AI activation cancellation when human responds."""
        conversation_id = uuid4()
        delay_seconds = 1  # Short delay for testing

        # Mock conversation that becomes human active during delay
        mock_conversation = MagicMock()
        mock_conversation.human_active = True
        mock_conversation.ai_active = False

        with patch.object(conversation_service, 'get_conversation', return_value=mock_conversation):
            with patch.object(conversation_service, 'update_conversation') as mock_update:
                await conversation_service._schedule_ai_activation(conversation_id, delay_seconds)

                # AI should not be activated since human is active
                mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_conversation_message_stats(self, conversation_service):
        """Test updating conversation message statistics."""
        conversation_id = uuid4()
        sender = "ai"
        message_time = datetime.utcnow()

        with patch('src.as_call_service.services.conversation_service.query') as mock_query:
            await conversation_service._update_conversation_message_stats(
                conversation_id, sender, message_time
            )

            # Verify update query was called
            mock_query.assert_called_once()
            query_sql = mock_query.call_args[0][0]
            assert "UPDATE conversations" in query_sql
            assert "ai_message_count = ai_message_count + 1" in query_sql