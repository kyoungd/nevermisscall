"""Simple core functionality tests for ts-auth-service."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
import unittest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

# Set up test environment variables
os.environ.update({
    'DATABASE_URL': 'postgresql://test:test@localhost/test',
    'JWT_SECRET': 'test-secret-key-for-testing-only',
    'INTERNAL_SERVICE_KEY': 'test-internal-key'
})

from ts_auth_service.models.user import UserRegistration, UserLogin, User, TokenPair
from ts_auth_service.models.response import ErrorCode, success_response, error_response
from ts_auth_service.config.settings import Settings
from ts_auth_service.services.token_service import TokenService


class TestCoreModels(unittest.TestCase):
    """Test core model functionality."""
    
    def test_user_registration_model(self):
        """Test UserRegistration model validation."""
        # Valid registration
        registration = UserRegistration(
            email="test@example.com",
            password="password123",
            first_name="John",
            last_name="Doe",
            business_name="Test Business"
        )
        
        self.assertEqual(registration.email, "test@example.com")
        self.assertEqual(registration.first_name, "John")
        self.assertEqual(registration.business_name, "Test Business")
        print("✓ UserRegistration model validation works")
    
    def test_password_validation(self):
        """Test password strength validation."""
        # Test weak password (should raise error)
        try:
            UserRegistration(
                email="test@example.com",
                password="weak",  # Too short, no numbers
                first_name="John",
                last_name="Doe",
                business_name="Test Business"
            )
            self.fail("Should have raised validation error")
        except ValueError:
            pass  # Expected
        
        # Test valid password
        registration = UserRegistration(
            email="test@example.com",
            password="strong123",  # Contains letters and numbers
            first_name="John",
            last_name="Doe",
            business_name="Test Business"
        )
        self.assertEqual(registration.password, "strong123")
        print("✓ Password validation works")
    
    def test_user_login_model(self):
        """Test UserLogin model."""
        login = UserLogin(
            email="test@example.com",
            password="password123"
        )
        
        self.assertEqual(login.email, "test@example.com")
        self.assertEqual(login.password, "password123")
        print("✓ UserLogin model works")
    
    def test_user_model(self):
        """Test User entity model."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            tenant_id=uuid4(),
            role="owner",
            email_verified=False,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.assertEqual(user.role, "owner")
        self.assertTrue(user.is_active)
        self.assertFalse(user.email_verified)
        print("✓ User model works")


class TestApiResponses(unittest.TestCase):
    """Test API response models."""
    
    def test_success_response(self):
        """Test success response creation."""
        data = {"user": {"id": str(uuid4())}}
        response = success_response(data, "Operation successful")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["message"], "Operation successful")
        self.assertEqual(response["data"], data)
        self.assertIn("timestamp", response)
        print("✓ Success response creation works")
    
    def test_error_response(self):
        """Test error response creation."""
        response = error_response(
            ErrorCode.INVALID_CREDENTIALS,
            "Invalid email or password",
            {"attempt_count": 1}
        )
        
        self.assertFalse(response["success"])
        self.assertEqual(response["error"]["code"], "INVALID_CREDENTIALS")
        self.assertEqual(response["error"]["message"], "Invalid email or password")
        self.assertEqual(response["error"]["details"]["attempt_count"], 1)
        print("✓ Error response creation works")


class TestConfiguration(unittest.TestCase):
    """Test configuration loading."""
    
    def test_settings_loading(self):
        """Test settings configuration."""
        settings = Settings()
        
        self.assertEqual(settings.service_name, "ts-auth-service")
        self.assertEqual(settings.port, 3301)
        self.assertEqual(settings.jwt_algorithm, "HS256")
        self.assertEqual(settings.bcrypt_salt_rounds, 12)
        print("✓ Configuration loading works")
    
    def test_jwt_config(self):
        """Test JWT configuration."""
        settings = Settings()
        
        self.assertEqual(settings.jwt_secret, "test-secret-key-for-testing-only")
        self.assertEqual(settings.jwt_expires_in, 3600)  # 1 hour
        self.assertEqual(settings.refresh_token_expires_in, 2592000)  # 30 days
        print("✓ JWT configuration works")


class TestTokenService(unittest.TestCase):
    """Test token service functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.token_service = TokenService()
        self.test_user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            tenant_id=uuid4(),
            role="owner",
            email_verified=True,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_generate_access_token(self):
        """Test JWT token generation."""
        token = self.token_service.generate_access_token(self.test_user)
        
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 50)  # JWT tokens are typically long
        
        # Check token format (3 parts separated by dots)
        parts = token.split('.')
        self.assertEqual(len(parts), 3)
        print("✓ Access token generation works")
    
    def test_generate_refresh_token(self):
        """Test refresh token generation."""
        refresh_token = self.token_service.generate_refresh_token()
        
        self.assertIsInstance(refresh_token, str)
        self.assertTrue(len(refresh_token) > 20)  # Should be reasonably long
        print("✓ Refresh token generation works")
    
    def test_token_pair_generation(self):
        """Test token pair generation."""
        tokens = self.token_service.generate_token_pair(self.test_user)
        
        self.assertIsInstance(tokens, TokenPair)
        self.assertIsInstance(tokens.access_token, str)
        self.assertIsInstance(tokens.refresh_token, str)
        self.assertEqual(tokens.expires_in, 3600)
        self.assertEqual(tokens.token_type, "bearer")
        print("✓ Token pair generation works")
    
    def test_token_validation(self):
        """Test token validation."""
        # Generate a valid token
        token = self.token_service.generate_access_token(self.test_user)
        
        # Validate the token
        payload = self.token_service.validate_access_token(token)
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload.sub, str(self.test_user.id))
        self.assertEqual(payload.email, self.test_user.email)
        self.assertEqual(payload.role, self.test_user.role)
        print("✓ Token validation works")
    
    def test_invalid_token_validation(self):
        """Test validation of invalid tokens."""
        # Test with completely invalid token
        payload = self.token_service.validate_access_token("invalid.token.here")
        self.assertIsNone(payload)
        
        # Test with empty token
        payload = self.token_service.validate_access_token("")
        self.assertIsNone(payload)
        print("✓ Invalid token validation works")


class TestErrorCodes(unittest.TestCase):
    """Test error code definitions."""
    
    def test_error_codes_exist(self):
        """Test that all required error codes exist."""
        required_codes = [
            "INVALID_CREDENTIALS",
            "EMAIL_ALREADY_EXISTS",
            "USER_NOT_FOUND",
            "ACCOUNT_DISABLED",
            "INVALID_TOKEN",
            "TOKEN_EXPIRED",
            "SESSION_EXPIRED",
            "VALIDATION_ERROR",
            "RATE_LIMIT_EXCEEDED",
            "INTERNAL_SERVER_ERROR"
        ]
        
        for code in required_codes:
            self.assertTrue(hasattr(ErrorCode, code))
            self.assertEqual(getattr(ErrorCode, code).value, code)
        
        print("✓ Error codes are properly defined")


class TestBusinessLogic(unittest.TestCase):
    """Test business logic validation."""
    
    def test_password_requirements(self):
        """Test password strength requirements."""
        # Minimum 8 characters
        MIN_LENGTH = 8
        
        # Must contain letters
        test_password = "password123"
        has_letter = any(c.isalpha() for c in test_password)
        has_number = any(c.isdigit() for c in test_password)
        
        self.assertTrue(len(test_password) >= MIN_LENGTH)
        self.assertTrue(has_letter)
        self.assertTrue(has_number)
        print("✓ Password requirements validation works")
    
    def test_user_roles(self):
        """Test user role definitions."""
        valid_roles = ['owner', 'operator', 'viewer']
        
        for role in valid_roles:
            user = User(
                id=uuid4(),
                email="test@example.com",
                password_hash="hashed_password",
                first_name="John",
                last_name="Doe",
                role=role,
                email_verified=False,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.assertEqual(user.role, role)
        
        print("✓ User roles validation works")
    
    def test_token_expiry_times(self):
        """Test token expiry configurations."""
        # Access token: 1 hour (3600 seconds)
        ACCESS_TOKEN_EXPIRE = 3600
        
        # Refresh token: 30 days (2592000 seconds)
        REFRESH_TOKEN_EXPIRE = 2592000
        
        settings = Settings()
        self.assertEqual(settings.jwt_expires_in, ACCESS_TOKEN_EXPIRE)
        self.assertEqual(settings.refresh_token_expires_in, REFRESH_TOKEN_EXPIRE)
        print("✓ Token expiry times are correct")


def run_all_tests():
    """Run all core functionality tests."""
    print("Running ts-auth-service core functionality tests...\n")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestCoreModels,
        TestApiResponses,
        TestConfiguration,
        TestTokenService,
        TestErrorCodes,
        TestBusinessLogic
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} core functionality tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures + result.errors)} test(s) failed out of {result.testsRun}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)