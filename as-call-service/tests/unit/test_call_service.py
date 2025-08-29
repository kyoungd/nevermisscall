"""Unit tests for CallService."""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from src.as_call_service.models import (
    CallCreate,
    CallUpdate,
    CallWebhook,
)
from src.as_call_service.services.call_service import CallService
from src.as_call_service.utils import DatabaseError, ServiceError


class TestCallService:
    """Test cases for CallService."""

    @pytest.fixture
    def call_service(self):
        """Create CallService instance for testing."""
        return CallService()

    @pytest.fixture
    def sample_call_create(self):
        """Sample CallCreate data for testing."""
        return CallCreate(
            call_sid="CA1234567890abcdef",
            tenant_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
            direction="inbound",
            status="ringing",
            start_time=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_call_webhook(self):
        """Sample CallWebhook data for testing."""
        return CallWebhook(
            callSid="CA1234567890abcdef",
            from_="+12125551234",
            to="+13105551234",
            tenant_id=uuid4(),
            call_status="ringing",
            direction="inbound",
            timestamp=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_create_call_success(self, call_service, sample_call_create):
        """Test successful call creation."""
        call_id = uuid4()
        mock_call_data = {
            'id': call_id,
            'call_sid': sample_call_create.call_sid,
            'tenant_id': sample_call_create.tenant_id,
            'customer_phone': sample_call_create.customer_phone,
            'business_phone': sample_call_create.business_phone,
            'direction': sample_call_create.direction,
            'status': sample_call_create.status,
            'start_time': sample_call_create.start_time,
            'end_time': None,
            'duration': 0,
            'processed': False,
            'sms_triggered': False,
            'conversation_created': False,
            'lead_created': False,
            'conversation_id': None,
            'lead_id': None,
            'caller_city': None,
            'caller_state': None,
            'caller_country': 'US',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }

        with patch('src.as_call_service.services.call_service.query') as mock_query:
            with patch('src.as_call_service.services.call_service.uuid4', return_value=call_id):
                # Mock database insert
                mock_query.side_effect = [None, [mock_call_data]]  # insert, then select

                result = await call_service.create_call(sample_call_create)

                # Verify call was inserted
                assert mock_query.call_count == 2
                insert_call = mock_query.call_args_list[0]
                assert "INSERT INTO calls" in insert_call[0][0]
                
                # Verify result
                assert result.id == call_id
                assert result.call_sid == sample_call_create.call_sid
                assert result.status == sample_call_create.status

    @pytest.mark.asyncio
    async def test_create_call_missing_required_field(self, call_service):
        """Test call creation with missing required field."""
        invalid_call_data = CallCreate(
            call_sid="",  # Missing required field
            tenant_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
            direction="inbound",
            status="ringing",
            start_time=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="call_sid is required"):
            await call_service.create_call(invalid_call_data)

    @pytest.mark.asyncio
    async def test_create_call_database_error(self, call_service, sample_call_create):
        """Test call creation with database error."""
        with patch('src.as_call_service.services.call_service.query') as mock_query:
            mock_query.side_effect = Exception("Database connection failed")

            with pytest.raises(DatabaseError, match="Failed to create call"):
                await call_service.create_call(sample_call_create)

    @pytest.mark.asyncio
    async def test_get_call_by_sid_success(self, call_service):
        """Test successful get call by SID."""
        call_sid = "CA1234567890abcdef"
        mock_call_data = {
            'id': uuid4(),
            'call_sid': call_sid,
            'tenant_id': uuid4(),
            'customer_phone': '+12125551234',
            'business_phone': '+13105551234',
            'direction': 'inbound',
            'status': 'completed',
            'start_time': datetime.utcnow(),
            'end_time': datetime.utcnow(),
            'duration': 30,
            'processed': True,
            'sms_triggered': False,
            'conversation_created': False,
            'lead_created': False,
            'conversation_id': None,
            'lead_id': None,
            'caller_city': None,
            'caller_state': None,
            'caller_country': 'US',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }

        with patch('src.as_call_service.services.call_service.query') as mock_query:
            mock_query.return_value = [mock_call_data]

            result = await call_service.get_call_by_sid(call_sid)

            # Verify query was called correctly
            mock_query.assert_called_once()
            assert "WHERE call_sid = $1" in mock_query.call_args[0][0]
            assert mock_query.call_args[0][1] == [call_sid]

            # Verify result
            assert result is not None
            assert result.call_sid == call_sid
            assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_get_call_by_sid_not_found(self, call_service):
        """Test get call by SID when call doesn't exist."""
        call_sid = "CA1234567890abcdef"

        with patch('src.as_call_service.services.call_service.query') as mock_query:
            mock_query.return_value = []  # No results

            result = await call_service.get_call_by_sid(call_sid)

            assert result is None

    @pytest.mark.asyncio
    async def test_update_call_success(self, call_service):
        """Test successful call update."""
        call_id = uuid4()
        update_data = CallUpdate(status="completed", duration=45)

        # Mock the get_call method to return updated call
        mock_updated_call = MagicMock()
        mock_updated_call.status = "completed"
        mock_updated_call.duration = 45

        with patch('src.as_call_service.services.call_service.query') as mock_query:
            with patch.object(call_service, 'get_call', return_value=mock_updated_call):
                result = await call_service.update_call(call_id, update_data)

                # Verify update query was called
                mock_query.assert_called_once()
                assert "UPDATE calls" in mock_query.call_args[0][0]
                assert "WHERE id = " in mock_query.call_args[0][0]

                # Verify result
                assert result == mock_updated_call

    @pytest.mark.asyncio
    async def test_process_incoming_call_new_call(self, call_service, sample_call_webhook):
        """Test processing incoming call for new call."""
        mock_call = MagicMock()
        mock_call.id = uuid4()
        mock_call.tenant_id = sample_call_webhook.tenant_id

        with patch.object(call_service, 'get_call_by_sid', return_value=None):  # New call
            with patch.object(call_service, 'create_call', return_value=mock_call):
                with patch('src.as_call_service.services.call_service.service_client') as mock_client:
                    mock_client.broadcast_realtime_event = AsyncMock()

                    result = await call_service.process_incoming_call(sample_call_webhook)

                    # Verify call was created
                    assert result == mock_call

                    # Verify real-time event was broadcast
                    mock_client.broadcast_realtime_event.assert_called_once()
                    event_args = mock_client.broadcast_realtime_event.call_args[1]
                    assert event_args['event_type'] == 'call_incoming'

    @pytest.mark.asyncio
    async def test_process_incoming_call_existing_call(self, call_service, sample_call_webhook):
        """Test processing incoming call for existing call."""
        existing_call = MagicMock()

        with patch.object(call_service, 'get_call_by_sid', return_value=existing_call):
            result = await call_service.process_incoming_call(sample_call_webhook)

            # Should return existing call without creating new one
            assert result == existing_call

    @pytest.mark.asyncio
    async def test_process_missed_call_success(self, call_service):
        """Test successful missed call processing."""
        call_sid = "CA1234567890abcdef"
        webhook_data = {
            'endTime': datetime.utcnow(),
            'callDuration': 0
        }

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

                                result = await call_service.process_missed_call(call_sid, webhook_data)

                                # Verify result
                                assert result == mock_call

                                # Verify real-time event was broadcast
                                mock_client.broadcast_realtime_event.assert_called_once()
                                event_args = mock_client.broadcast_realtime_event.call_args[1]
                                assert event_args['event_type'] == 'call_missed'

    @pytest.mark.asyncio
    async def test_process_missed_call_not_found(self, call_service):
        """Test processing missed call when call doesn't exist."""
        call_sid = "CA1234567890abcdef"
        webhook_data = {}

        with patch.object(call_service, 'get_call_by_sid', return_value=None):
            with pytest.raises(Exception):  # HTTPException would be raised
                await call_service.process_missed_call(call_sid, webhook_data)

    @pytest.mark.asyncio
    async def test_send_auto_response_sms_success(self, call_service):
        """Test successful auto-response SMS sending."""
        mock_call = MagicMock()
        mock_call.tenant_id = uuid4()
        mock_call.customer_phone = "+12125551234"
        mock_call.business_phone = "+13105551234"

        mock_conversation = MagicMock()
        mock_conversation.id = uuid4()

        with patch('src.as_call_service.services.call_service.service_client') as mock_client:
            mock_client.validate_tenant_and_service_area = AsyncMock(return_value={
                'businessName': 'Test Business'
            })
            mock_client.send_sms_via_twilio_server = AsyncMock()

            await call_service._send_auto_response_sms(mock_call, mock_conversation)

            # Verify SMS was sent
            mock_client.send_sms_via_twilio_server.assert_called_once()
            sms_args = mock_client.send_sms_via_twilio_server.call_args[1]
            assert sms_args['to_phone'] == mock_call.customer_phone
            assert sms_args['from_phone'] == mock_call.business_phone
            assert 'Test Business' in sms_args['message']

    @pytest.mark.asyncio
    async def test_send_auto_response_sms_failure(self, call_service):
        """Test auto-response SMS sending failure."""
        mock_call = MagicMock()
        mock_call.tenant_id = uuid4()

        mock_conversation = MagicMock()

        with patch('src.as_call_service.services.call_service.service_client') as mock_client:
            mock_client.validate_tenant_and_service_area = AsyncMock(side_effect=Exception("Service error"))

            with pytest.raises(ServiceError, match="Failed to send auto-response SMS"):
                await call_service._send_auto_response_sms(mock_call, mock_conversation)