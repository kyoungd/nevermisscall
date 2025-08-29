"""Test authentication service."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from src.as_connection_service.services.auth_service import AuthService


class TestAuthService:
    """Test AuthService class."""
    
    @pytest.fixture
    async def auth_service(self):
        """Create auth service instance."""
        return AuthService()
    
    @pytest.mark.asyncio
    async def test_validate_jwt_token_success(self, auth_service):
        """Test successful JWT token validation."""
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "user": {
                "user_id": "user-123",
                "tenant_id": "tenant-456",
                "email": "test@example.com",
                "permissions": ["read", "write"]
            }
        }
        
        with patch.object(auth_service.client, 'post', return_value=mock_response):
            result = await auth_service.validate_jwt_token("valid-token")
        
        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_validate_jwt_token_invalid(self, auth_service):
        """Test invalid JWT token validation."""
        # Mock HTTP response for invalid token
        mock_response = AsyncMock()
        mock_response.status_code = 401
        
        with patch.object(auth_service.client, 'post', return_value=mock_response):
            result = await auth_service.validate_jwt_token("invalid-token")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_jwt_token_service_error(self, auth_service):
        """Test JWT token validation with service error."""
        # Mock HTTP response for service error
        mock_response = AsyncMock()
        mock_response.status_code = 500
        
        with patch.object(auth_service.client, 'post', return_value=mock_response):
            result = await auth_service.validate_jwt_token("any-token")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_jwt_token_network_error(self, auth_service):
        """Test JWT token validation with network error."""
        with patch.object(auth_service.client, 'post', side_effect=httpx.RequestError("Network error")):
            result = await auth_service.validate_jwt_token("any-token")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_authenticate_socket_connection_success(self, auth_service):
        """Test successful socket authentication."""
        # Mock validate_jwt_token
        mock_user_data = {
            "user_id": "user-123",
            "tenant_id": "tenant-456",
            "email": "test@example.com",
            "permissions": ["read", "write"]
        }
        
        with patch.object(auth_service, 'validate_jwt_token', return_value=mock_user_data):
            result = await auth_service.authenticate_socket_connection("valid-token")
        
        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["tenant_id"] == "tenant-456"
        assert result["email"] == "test@example.com"
        assert result["permissions"] == ["read", "write"]
    
    @pytest.mark.asyncio
    async def test_authenticate_socket_connection_failure(self, auth_service):
        """Test failed socket authentication."""
        with patch.object(auth_service, 'validate_jwt_token', return_value=None):
            result = await auth_service.authenticate_socket_connection("invalid-token")
        
        assert result is None
    
    def test_validate_service_key_valid(self, auth_service):
        """Test valid service key validation."""
        result = auth_service.validate_service_key("nmc-internal-services-auth-key-phase1")
        assert result is True
    
    def test_validate_service_key_invalid(self, auth_service):
        """Test invalid service key validation."""
        result = auth_service.validate_service_key("wrong-service-key")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_user_tenant_access_success(self, auth_service):
        """Test successful user tenant access check."""
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"has_access": True}
        
        with patch.object(auth_service.client, 'post', return_value=mock_response):
            result = await auth_service.check_user_tenant_access("user-123", "tenant-456")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_user_tenant_access_denied(self, auth_service):
        """Test denied user tenant access check."""
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"has_access": False}
        
        with patch.object(auth_service.client, 'post', return_value=mock_response):
            result = await auth_service.check_user_tenant_access("user-123", "wrong-tenant")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_user_tenant_access_error(self, auth_service):
        """Test user tenant access check with error."""
        # Mock HTTP response error
        mock_response = AsyncMock()
        mock_response.status_code = 500
        
        with patch.object(auth_service.client, 'post', return_value=mock_response):
            result = await auth_service.check_user_tenant_access("user-123", "tenant-456")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_decode_token_locally_success(self, auth_service):
        """Test local JWT token decoding."""
        # Mock jose.jwt.decode
        mock_payload = {
            "user_id": "user-123",
            "tenant_id": "tenant-456",
            "exp": 1234567890
        }
        
        with patch('src.as_connection_service.services.auth_service.jwt.decode', return_value=mock_payload):
            result = await auth_service.decode_token_locally("valid-token", "secret-key")
        
        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["tenant_id"] == "tenant-456"
    
    @pytest.mark.asyncio
    async def test_decode_token_locally_invalid(self, auth_service):
        """Test local JWT token decoding with invalid token."""
        from jose import JWTError
        
        with patch('src.as_connection_service.services.auth_service.jwt.decode', side_effect=JWTError("Invalid token")):
            result = await auth_service.decode_token_locally("invalid-token", "secret-key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_close(self, auth_service):
        """Test closing auth service."""
        with patch.object(auth_service.client, 'aclose') as mock_close:
            await auth_service.close()
            mock_close.assert_called_once()