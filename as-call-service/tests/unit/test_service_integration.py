"""Service integration tests - focused on external service communication."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from src.as_call_service.utils.http_client import ServiceClient


class TestExternalServiceIntegration:
    """Test integration with external services - core communication patterns."""

    @pytest.fixture
    def service_client(self):
        return ServiceClient()

    @pytest.mark.asyncio
    async def test_sms_sending_via_twilio_server(self, service_client):
        """Test SMS sending through twilio-server."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messageSid": "SM123", "status": "sent"}
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await service_client.send_sms_via_twilio_server(
                to_phone="+12125551234",
                from_phone="+13105551234",
                message="Test message",
                tenant_id=str(uuid4())
            )

            # Verify request was made correctly
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args[1]['method'] == 'POST'
            assert '/internal/sms/send' in call_args[1]['url']
            
            # Verify response
            assert result["messageSid"] == "SM123"

    @pytest.mark.asyncio
    async def test_ai_conversation_processing(self, service_client):
        """Test AI conversation processing through dispatch-bot-ai."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "aiResponse": {
                    "message": "I can help with that!",
                    "confidence": 0.85,
                    "intent": "schedule_service"
                }
            }
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await service_client.process_ai_conversation(
                conversation_id=str(uuid4()),
                message_content="I need help with my sink",
                conversation_history=["Hi! Sorry we missed your call."],
                tenant_context={"businessName": "Test Plumbing"}
            )

            # Verify request was made correctly
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert '/dispatch/process' in call_args[1]['url']
            
            # Verify response
            assert result["aiResponse"]["message"] == "I can help with that!"

    @pytest.mark.asyncio
    async def test_tenant_validation(self, service_client):
        """Test tenant validation through ts-tenant-service."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "exists": True,
                "active": True,
                "businessName": "Test Business",
                "serviceAreaValid": True,
                "addressValidated": True
            }
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await service_client.validate_tenant_and_service_area(
                tenant_id=str(uuid4()),
                customer_address="123 Main St"
            )

            # Verify request was made correctly
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert '/internal/tenants/' in call_args[1]['url']
            assert '/validate' in call_args[1]['url']
            
            # Verify response
            assert result["businessName"] == "Test Business"
            assert result["serviceAreaValid"] is True

    @pytest.mark.asyncio
    async def test_realtime_event_broadcasting(self, service_client):
        """Test real-time event broadcasting through as-connection-service."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Should not raise exception even if successful
            await service_client.broadcast_realtime_event(
                tenant_id=str(uuid4()),
                event_type="call_incoming",
                event_data={"callId": str(uuid4())}
            )

            # Verify request was made
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert '/internal/events/broadcast' in call_args[1]['url']

    @pytest.mark.asyncio
    async def test_service_timeout_handling(self, service_client):
        """Test service timeout handling."""
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(Exception):  # Should raise HTTPException 504
                await service_client.send_sms_via_twilio_server(
                    to_phone="+12125551234",
                    from_phone="+13105551234",
                    message="Test",
                    tenant_id=str(uuid4())
                )

    @pytest.mark.asyncio
    async def test_service_error_handling(self, service_client):
        """Test service error response handling."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(Exception):  # Should raise HTTPException
                await service_client.send_sms_via_twilio_server(
                    to_phone="+12125551234",
                    from_phone="+13105551234",
                    message="Test",
                    tenant_id=str(uuid4())
                )

    @pytest.mark.asyncio
    async def test_realtime_broadcast_failure_handling(self, service_client):
        """Test realtime broadcast failure doesn't crash main operation."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.request = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Should not raise exception - realtime broadcast failures are non-critical
            await service_client.broadcast_realtime_event(
                tenant_id=str(uuid4()),
                event_type="test_event",
                event_data={}
            )


class TestAuthenticationIntegration:
    """Test authentication and authorization integration."""

    def test_service_key_header_inclusion(self):
        """Test service key is included in internal requests."""
        from src.as_call_service.config import settings
        
        service_client = ServiceClient()
        
        # Verify internal service key is in headers
        assert service_client.headers["x-service-key"] == settings.internal_service_key
        assert service_client.headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_jwt_token_validation_flow(self):
        """Test JWT token validation in auth utils."""
        from src.as_call_service.utils.auth import verify_jwt_token
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock JWT token
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="mock.jwt.token"
        )
        
        with patch('src.as_call_service.utils.auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {
                "user_id": str(uuid4()),
                "tenant_id": str(uuid4()),
                "email": "test@example.com",
                "role": "admin"
            }
            
            with patch('src.as_call_service.utils.auth.settings') as mock_settings:
                mock_settings.jwt_secret = "test-secret"
                
                result = await verify_jwt_token(mock_credentials)
                
                assert "user_id" in result
                assert "tenant_id" in result

    @pytest.mark.asyncio
    async def test_tenant_access_verification(self):
        """Test tenant access verification logic."""
        from src.as_call_service.utils.auth import verify_tenant_access
        
        user_tenant_id = uuid4()
        resource_tenant_id = uuid4()
        
        user_data = {
            "user_id": uuid4(),
            "tenant_id": user_tenant_id,
        }
        
        # Should raise exception for different tenant
        with pytest.raises(Exception):  # HTTPException 403
            verify_tenant_access(user_data, resource_tenant_id)
        
        # Should not raise exception for same tenant
        verify_tenant_access(user_data, user_tenant_id)


class TestSharedLibraryIntegration:
    """Test shared library integration patterns."""

    def test_shared_logger_integration(self):
        """Test shared logger is properly integrated."""
        from src.as_call_service.utils.shared_integration import logger
        
        # Should have logger instance
        assert logger is not None
        
        # Should support standard log methods
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_shared_database_integration(self):
        """Test shared database functions are available."""
        from src.as_call_service.utils.shared_integration import query, health_check, init_database
        
        # Should have database functions
        assert callable(query)
        assert callable(health_check)
        assert callable(init_database)

    def test_shared_response_helpers(self):
        """Test shared response helpers."""
        from src.as_call_service.utils.shared_integration import successResponse, errorResponse
        
        # Success response
        success = successResponse({"test": "data"}, "Success message")
        assert success["success"] is True
        assert success["data"]["test"] == "data"
        
        # Error response
        error = errorResponse("TEST_ERROR", "Error message", {"field": "value"})
        assert error["success"] is False
        assert error["error"]["code"] == "TEST_ERROR"

    def test_shared_validation_helpers(self):
        """Test shared validation helpers."""
        from src.as_call_service.utils.shared_integration import validateRequired
        
        # Should not raise for valid values
        validateRequired("valid-value", "field_name")
        
        # Should raise for invalid values
        with pytest.raises(Exception):
            validateRequired("", "field_name")
        
        with pytest.raises(Exception):
            validateRequired(None, "field_name")