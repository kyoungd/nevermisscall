"""API validation tests - focused on request/response validation."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
from fastapi import HTTPException

from src.as_call_service.main import app


class TestAPIValidation:
    """Test API endpoint validation - core request/response handling."""

    @pytest.fixture
    def client(self):
        return AsyncClient(app=app, base_url="http://test")

    @pytest.mark.asyncio
    async def test_incoming_call_requires_auth(self, client):
        """Test incoming call endpoint requires service key."""
        webhook_data = {
            "callSid": "CA123",
            "from": "+12125551234",
            "to": "+13105551234",
        }

        # Without auth header
        response = await client.post("/calls/incoming", json=webhook_data)
        assert response.status_code == 401

        # With wrong auth header
        response = await client.post(
            "/calls/incoming",
            json=webhook_data,
            headers={"x-service-key": "wrong-key"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_incoming_call_validates_required_fields(self, client):
        """Test incoming call validates required fields."""
        # Missing required fields
        incomplete_data = {
            "from": "+12125551234",
            # Missing callSid, to, etc.
        }

        with patch('src.as_call_service.utils.auth.verify_internal_service_key', return_value="valid"):
            response = await client.post(
                "/calls/incoming",
                json=incomplete_data,
                headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
            )
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_human_reply_requires_jwt(self, client):
        """Test human reply endpoint requires JWT authentication."""
        conversation_id = uuid4()
        reply_data = {"message": "I can help!"}

        # Without JWT
        response = await client.post(f"/conversations/{conversation_id}/reply", json=reply_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_human_reply_validates_message_content(self, client):
        """Test human reply validates message content."""
        conversation_id = uuid4()
        
        # Mock JWT auth
        mock_user_data = {"user_id": uuid4(), "tenant_id": uuid4()}
        
        with patch('src.as_call_service.utils.auth.verify_jwt_token', return_value=mock_user_data):
            # Empty message
            response = await client.post(
                f"/conversations/{conversation_id}/reply",
                json={"message": ""},
                headers={"Authorization": "Bearer valid-token"}
            )
            assert response.status_code == 422

            # Too long message
            response = await client.post(
                f"/conversations/{conversation_id}/reply",
                json={"message": "A" * 1601},
                headers={"Authorization": "Bearer valid-token"}
            )
            assert response.status_code == 400  # Validation error

    @pytest.mark.asyncio
    async def test_get_call_validates_tenant_access(self, client):
        """Test get call endpoint validates tenant access."""
        call_id = uuid4()
        call_tenant_id = uuid4()
        user_tenant_id = uuid4()  # Different tenant
        
        # Mock call with different tenant
        mock_call = MagicMock()
        mock_call.tenant_id = call_tenant_id
        
        # Mock user with different tenant
        mock_user_data = {"user_id": uuid4(), "tenant_id": user_tenant_id}

        with patch('src.as_call_service.utils.auth.verify_jwt_token', return_value=mock_user_data):
            with patch('src.as_call_service.services.call_service.call_service.get_call', return_value=mock_call):
                response = await client.get(
                    f"/calls/{call_id}",
                    headers={"Authorization": "Bearer valid-token"}
                )
                assert response.status_code == 403  # Forbidden

    @pytest.mark.asyncio
    async def test_health_endpoint_basic(self, client):
        """Test health endpoint basic functionality."""
        with patch('src.as_call_service.controllers.health_controller.health_check', return_value=True):
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_process_message_validates_content(self, client):
        """Test message processing validates content."""
        conversation_id = uuid4()
        
        with patch('src.as_call_service.utils.auth.verify_internal_service_key', return_value="valid"):
            # Missing message body
            response = await client.post(
                f"/conversations/{conversation_id}/messages",
                json={"messageSid": "SM123"},
                headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
            )
            assert response.status_code == 400

            # Invalid message content (XSS)
            response = await client.post(
                f"/conversations/{conversation_id}/messages",
                json={
                    "messageSid": "SM123",
                    "body": "<script>alert('xss')</script>"
                },
                headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_lead_status_update_validation(self, client):
        """Test lead status update validation."""
        lead_id = uuid4()
        tenant_id = uuid4()
        
        mock_lead = MagicMock()
        mock_lead.tenant_id = tenant_id
        
        mock_user_data = {"user_id": uuid4(), "tenant_id": tenant_id}

        with patch('src.as_call_service.utils.auth.verify_jwt_token', return_value=mock_user_data):
            with patch('src.as_call_service.services.lead_service.lead_service.get_lead', return_value=mock_lead):
                # Invalid status
                response = await client.put(
                    f"/leads/{lead_id}/status",
                    json={"status": "invalid_status"},
                    headers={"Authorization": "Bearer valid-token"}
                )
                assert response.status_code == 422  # Validation error

                # Valid status
                mock_updated_lead = MagicMock()
                mock_updated_lead.status = "qualified"
                mock_updated_lead.updated_at = datetime.utcnow()
                
                with patch('src.as_call_service.services.lead_service.lead_service.update_lead_status', return_value=mock_updated_lead):
                    response = await client.put(
                        f"/leads/{lead_id}/status",
                        json={"status": "qualified"},
                        headers={"Authorization": "Bearer valid-token"}
                    )
                    assert response.status_code == 200


class TestErrorResponses:
    """Test error response handling."""

    @pytest.fixture
    def client(self):
        return AsyncClient(app=app, base_url="http://test")

    @pytest.mark.asyncio
    async def test_404_error_handling(self, client):
        """Test 404 error responses."""
        mock_user_data = {"user_id": uuid4(), "tenant_id": uuid4()}
        
        with patch('src.as_call_service.utils.auth.verify_jwt_token', return_value=mock_user_data):
            with patch('src.as_call_service.services.call_service.call_service.get_call') as mock_get:
                mock_get.side_effect = HTTPException(status_code=404, detail="Call not found")
                
                response = await client.get(
                    f"/calls/{uuid4()}",
                    headers={"Authorization": "Bearer valid-token"}
                )
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_500_error_handling(self, client):
        """Test internal server error handling."""
        with patch('src.as_call_service.controllers.health_controller.health_check') as mock_health:
            mock_health.side_effect = Exception("Database connection failed")
            
            response = await client.get("/health")
            assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, client):
        """Test service unavailable error handling."""
        webhook_data = {
            "callSid": "CA123",
            "from": "+12125551234",
            "to": "+13105551234",
            "tenantId": str(uuid4()),
            "callStatus": "ringing",
            "direction": "inbound",
        }

        with patch('src.as_call_service.utils.auth.verify_internal_service_key', return_value="valid"):
            with patch('src.as_call_service.services.call_service.call_service.process_incoming_call') as mock_process:
                # Mock service error
                from src.as_call_service.utils import ServiceError
                mock_process.side_effect = ServiceError("External service unavailable")
                
                response = await client.post(
                    "/calls/incoming",
                    json=webhook_data,
                    headers={"x-service-key": "nmc-internal-services-auth-key-phase1"}
                )
                assert response.status_code == 502  # Bad Gateway


class TestDataValidation:
    """Test data model validation."""

    def test_phone_number_format_validation(self):
        """Test phone number format validation in models."""
        from src.as_call_service.models import CallCreate
        
        # Valid phone number
        call_data = CallCreate(
            call_sid="CA123",
            tenant_id=uuid4(),
            customer_phone="+12125551234",
            business_phone="+13105551234",
            direction="inbound",
            status="ringing",
            start_time=datetime.utcnow(),
        )
        assert call_data.customer_phone == "+12125551234"

        # Invalid phone number should fail validation
        with pytest.raises(Exception):  # Pydantic validation error
            CallCreate(
                call_sid="CA123",
                tenant_id=uuid4(),
                customer_phone="invalid-phone",  # Invalid format
                business_phone="+13105551234",
                direction="inbound",
                status="ringing",
                start_time=datetime.utcnow(),
            )

    def test_message_length_validation(self):
        """Test message length validation."""
        from src.as_call_service.models import MessageCreate
        
        # Valid message
        message_data = MessageCreate(
            conversation_id=uuid4(),
            tenant_id=uuid4(),
            direction="inbound",
            sender="customer",
            body="Hello, I need help",
        )
        assert message_data.body == "Hello, I need help"

        # Too long message should fail
        with pytest.raises(Exception):  # Pydantic validation error
            MessageCreate(
                conversation_id=uuid4(),
                tenant_id=uuid4(),
                direction="inbound",
                sender="customer",
                body="A" * 1601,  # Too long
            )

    def test_lead_status_validation(self):
        """Test lead status validation."""
        from src.as_call_service.models import LeadStatusUpdate
        
        # Valid status
        status_update = LeadStatusUpdate(
            status="qualified",
            notes="Customer confirmed interest",
        )
        assert status_update.status == "qualified"

        # Invalid status should fail
        with pytest.raises(Exception):  # Pydantic validation error
            LeadStatusUpdate(
                status="invalid_status",  # Not in allowed enum
            )