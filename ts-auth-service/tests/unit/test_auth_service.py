"""Unit tests for authentication service."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

# Set up test environment variables
os.environ.update({
    'DATABASE_URL': 'postgresql://test:test@localhost/test',
    'JWT_SECRET': 'test-secret-key-for-testing-only',
    'INTERNAL_SERVICE_KEY': 'test-internal-key'
})

from ts_auth_service.services.auth_service import AuthService
from ts_auth_service.services.database import DatabaseService
from ts_auth_service.services.token_service import TokenService
from ts_auth_service.models.user import User, UserRegistration, UserLogin
from ts_auth_service.models.response import ErrorCode


class TestAuthService(unittest.IsolatedAsyncioTestCase):
    """Test authentication service methods."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.mock_database = AsyncMock(spec=DatabaseService)
        self.mock_token_service = MagicMock(spec=TokenService)
        
        self.auth_service = AuthService(self.mock_database, self.mock_token_service)
        
        # Test user data
        self.test_user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="$2b$12$hashed_password_here",
            first_name="John",
            last_name="Doe",
            tenant_id=uuid4(),
            role="owner",
            email_verified=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.test_registration = UserRegistration(
            email="test@example.com",
            password="password123",
            first_name="John",
            last_name="Doe",
            business_name="Test Business"
        )
        
        self.test_login = UserLogin(
            email="test@example.com",
            password="password123"
        )
    
    async def test_register_user_success(self):
        """Test successful user registration."""
        # Mock database responses
        self.mock_database.email_exists.return_value = False
        self.mock_database.create_user.return_value = self.test_user
        self.mock_database.create_session.return_value = MagicMock()
        self.mock_database.update_last_login.return_value = True
        
        # Mock token generation
        mock_tokens = MagicMock()
        self.mock_token_service.generate_token_pair.return_value = mock_tokens
        self.mock_token_service.get_refresh_token_expiry.return_value = datetime.now(timezone.utc)
        
        # Mock password hashing
        with patch.object(self.auth_service, '_hash_password', return_value="hashed_password"):
            success, result = await self.auth_service.register_user(self.test_registration)
        
        self.assertTrue(success)
        self.assertIn("user", result)
        self.assertIn("tokens", result)
        self.mock_database.email_exists.assert_called_once_with("test@example.com")
        self.mock_database.create_user.assert_called_once()
    
    async def test_register_user_email_exists(self):
        """Test registration with existing email."""
        # Mock email already exists
        self.mock_database.email_exists.return_value = True
        
        success, result = await self.auth_service.register_user(self.test_registration)
        
        self.assertFalse(success)
        self.assertEqual(result["error_code"], ErrorCode.EMAIL_ALREADY_EXISTS)
        self.assertIn("already exists", result["message"])
    
    async def test_login_user_success(self):
        """Test successful user login."""
        # Mock database responses
        self.mock_database.get_user_by_email.return_value = self.test_user
        self.mock_database.create_session.return_value = MagicMock()
        self.mock_database.update_last_login.return_value = True
        
        # Mock token generation
        mock_tokens = MagicMock()
        self.mock_token_service.generate_token_pair.return_value = mock_tokens
        self.mock_token_service.get_refresh_token_expiry.return_value = datetime.now(timezone.utc)
        
        # Mock password verification
        with patch.object(self.auth_service, '_verify_password', return_value=True):
            success, result = await self.auth_service.login_user(self.test_login)
        
        self.assertTrue(success)
        self.assertIn("user", result)
        self.assertIn("tokens", result)
        self.mock_database.get_user_by_email.assert_called_once_with("test@example.com")
    
    async def test_login_user_invalid_credentials(self):
        """Test login with invalid credentials."""
        # Mock user not found
        self.mock_database.get_user_by_email.return_value = None
        
        success, result = await self.auth_service.login_user(self.test_login)
        
        self.assertFalse(success)
        self.assertEqual(result["error_code"], ErrorCode.INVALID_CREDENTIALS)
        self.assertIn("Invalid email or password", result["message"])
    
    async def test_login_user_wrong_password(self):
        """Test login with wrong password."""
        # Mock database response
        self.mock_database.get_user_by_email.return_value = self.test_user
        
        # Mock password verification failure
        with patch.object(self.auth_service, '_verify_password', return_value=False):
            success, result = await self.auth_service.login_user(self.test_login)
        
        self.assertFalse(success)
        self.assertEqual(result["error_code"], ErrorCode.INVALID_CREDENTIALS)
    
    async def test_login_user_disabled_account(self):
        """Test login with disabled account."""
        # Create disabled user
        disabled_user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="$2b$12$hashed_password_here",
            first_name="John",
            last_name="Doe",
            role="owner",
            email_verified=False,
            is_active=False,  # Account disabled
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.mock_database.get_user_by_email.return_value = disabled_user
        
        success, result = await self.auth_service.login_user(self.test_login)
        
        self.assertFalse(success)
        self.assertEqual(result["error_code"], ErrorCode.ACCOUNT_DISABLED)
    
    async def test_refresh_token_success(self):
        """Test successful token refresh."""
        refresh_token = "valid_refresh_token"
        
        # Mock session
        mock_session = MagicMock()
        mock_session.is_active = True
        mock_session.expires_at = datetime.now(timezone.utc).replace(year=2030)  # Future date
        mock_session.user_id = self.test_user.id
        
        self.mock_database.get_session_by_token.return_value = mock_session
        self.mock_database.get_user_by_id.return_value = self.test_user
        
        # Mock token generation
        new_token = "new_access_token"
        self.mock_token_service.refresh_access_token.return_value = new_token
        self.mock_token_service.access_token_expire = 3600
        
        success, result = await self.auth_service.refresh_token(refresh_token)
        
        self.assertTrue(success)
        self.assertIn("tokens", result)
    
    async def test_refresh_token_invalid(self):
        """Test refresh with invalid token."""
        refresh_token = "invalid_refresh_token"
        
        # Mock no session found
        self.mock_database.get_session_by_token.return_value = None
        
        success, result = await self.auth_service.refresh_token(refresh_token)
        
        self.assertFalse(success)
        self.assertEqual(result["error_code"], ErrorCode.REFRESH_TOKEN_INVALID)
    
    async def test_refresh_token_expired_session(self):
        """Test refresh with expired session."""
        refresh_token = "expired_refresh_token"
        
        # Mock expired session
        mock_session = MagicMock()
        mock_session.is_active = True
        mock_session.expires_at = datetime.now(timezone.utc).replace(year=2020)  # Past date
        
        self.mock_database.get_session_by_token.return_value = mock_session
        self.mock_database.invalidate_session.return_value = True
        
        success, result = await self.auth_service.refresh_token(refresh_token)
        
        self.assertFalse(success)
        self.assertEqual(result["error_code"], ErrorCode.SESSION_EXPIRED)
        self.mock_database.invalidate_session.assert_called_once_with(refresh_token)
    
    async def test_logout_user_success(self):
        """Test successful user logout."""
        refresh_token = "valid_refresh_token"
        
        # Mock successful session invalidation
        self.mock_database.invalidate_session.return_value = True
        
        result = await self.auth_service.logout_user(refresh_token)
        
        self.assertTrue(result)
        self.mock_database.invalidate_session.assert_called_once_with(refresh_token)
    
    async def test_logout_user_failure(self):
        """Test logout failure."""
        refresh_token = "invalid_refresh_token"
        
        # Mock session invalidation failure
        self.mock_database.invalidate_session.return_value = False
        
        result = await self.auth_service.logout_user(refresh_token)
        
        self.assertFalse(result)
    
    async def test_validate_token_success(self):
        """Test successful token validation."""
        token = "valid_jwt_token"
        
        # Mock token service validation
        mock_payload = MagicMock()
        mock_payload.sub = str(self.test_user.id)
        self.mock_token_service.validate_token_format.return_value = True
        self.mock_token_service.validate_access_token.return_value = mock_payload
        
        # Mock database response
        self.mock_database.get_user_by_id.return_value = self.test_user
        
        valid, user, error = await self.auth_service.validate_token(token)
        
        self.assertTrue(valid)
        self.assertEqual(user, self.test_user)
        self.assertIsNone(error)
    
    async def test_validate_token_invalid_format(self):
        """Test token validation with invalid format."""
        token = "invalid_format_token"
        
        # Mock invalid token format
        self.mock_token_service.validate_token_format.return_value = False
        
        valid, user, error = await self.auth_service.validate_token(token)
        
        self.assertFalse(valid)
        self.assertIsNone(user)
        self.assertEqual(error, "Invalid token format")
    
    async def test_validate_token_expired(self):
        """Test token validation with expired token."""
        token = "expired_jwt_token"
        
        # Mock token format valid but validation fails
        self.mock_token_service.validate_token_format.return_value = True
        self.mock_token_service.validate_access_token.return_value = None
        
        valid, user, error = await self.auth_service.validate_token(token)
        
        self.assertFalse(valid)
        self.assertIsNone(user)
        self.assertEqual(error, "Invalid or expired token")
    
    async def test_get_user_profile_success(self):
        """Test getting user profile."""
        user_id = self.test_user.id
        
        # Mock database response
        self.mock_database.get_user_by_id.return_value = self.test_user
        
        result = await self.auth_service.get_user_profile(user_id)
        
        self.assertEqual(result, self.test_user)
        self.mock_database.get_user_by_id.assert_called_once_with(user_id)
    
    async def test_get_user_profile_not_found(self):
        """Test getting non-existent user profile."""
        user_id = uuid4()
        
        # Mock user not found
        self.mock_database.get_user_by_id.return_value = None
        
        result = await self.auth_service.get_user_profile(user_id)
        
        self.assertIsNone(result)
    
    async def test_password_hashing_and_verification(self):
        """Test password hashing and verification methods."""
        password = "test_password_123"
        
        # Test hashing
        hashed = self.auth_service._hash_password(password)
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(hashed, password)  # Should be different from original
        
        # Test verification with correct password
        is_valid = self.auth_service._verify_password(password, hashed)
        self.assertTrue(is_valid)
        
        # Test verification with wrong password
        is_valid = self.auth_service._verify_password("wrong_password", hashed)
        self.assertFalse(is_valid)
    
    async def test_password_strength_validation(self):
        """Test password strength validation."""
        # Test valid password
        valid, message = self.auth_service.validate_password_strength("password123")
        self.assertTrue(valid)
        self.assertEqual(message, "Password is valid")
        
        # Test too short
        valid, message = self.auth_service.validate_password_strength("short")
        self.assertFalse(valid)
        self.assertIn("at least", message)
        
        # Test no letters
        valid, message = self.auth_service.validate_password_strength("12345678")
        self.assertFalse(valid)
        self.assertIn("letter", message)
        
        # Test no numbers
        valid, message = self.auth_service.validate_password_strength("onlyletters")
        self.assertFalse(valid)
        self.assertIn("number", message)


if __name__ == "__main__":
    unittest.main()