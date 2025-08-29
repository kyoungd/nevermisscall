"""Unit tests for data models."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import unittest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from ts_auth_service.models.user import (
    UserRegistration, UserLogin, User, UserResponse, UserSession,
    JWTPayload, TokenPair, RefreshTokenRequest, TokenValidationRequest
)
from ts_auth_service.models.response import (
    ErrorCode, ErrorDetail, ApiResponse, SuccessResponse, ErrorResponse,
    success_response, error_response, auth_success_response
)


class TestUserModels(unittest.TestCase):
    """Test user-related models."""
    
    def test_user_registration_valid(self):
        """Test valid user registration model."""
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
    
    def test_user_registration_invalid_email(self):
        """Test user registration with invalid email."""
        with self.assertRaises(ValidationError):
            UserRegistration(
                email="invalid-email",
                password="password123",
                first_name="John",
                last_name="Doe",
                business_name="Test Business"
            )
    
    def test_user_registration_weak_password(self):
        """Test user registration with weak password."""
        with self.assertRaises(ValidationError):
            UserRegistration(
                email="test@example.com",
                password="weak",  # Too short, no numbers
                first_name="John",
                last_name="Doe",
                business_name="Test Business"
            )
    
    def test_user_registration_password_no_letters(self):
        """Test password validation - no letters."""
        with self.assertRaises(ValidationError):
            UserRegistration(
                email="test@example.com",
                password="12345678",  # Only numbers
                first_name="John",
                last_name="Doe",
                business_name="Test Business"
            )
    
    def test_user_registration_password_no_numbers(self):
        """Test password validation - no numbers."""
        with self.assertRaises(ValidationError):
            UserRegistration(
                email="test@example.com",
                password="onlyletters",  # No numbers
                first_name="John",
                last_name="Doe",
                business_name="Test Business"
            )
    
    def test_user_login_model(self):
        """Test user login model."""
        login = UserLogin(
            email="test@example.com",
            password="password123"
        )
        
        self.assertEqual(login.email, "test@example.com")
        self.assertEqual(login.password, "password123")
    
    def test_user_model_complete(self):
        """Test complete user model."""
        user_id = uuid4()
        tenant_id = uuid4()
        now = datetime.utcnow()
        
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="$2b$12$hashed_password",
            first_name="John",
            last_name="Doe",
            tenant_id=tenant_id,
            role="owner",
            email_verified=True,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login_at=now
        )
        
        self.assertEqual(user.id, user_id)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.role, "owner")
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
    
    def test_user_response_model(self):
        """Test user response model (no sensitive data)."""
        user_id = uuid4()
        now = datetime.utcnow()
        
        user_response = UserResponse(
            id=user_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            created_at=now
        )
        
        self.assertEqual(user_response.id, user_id)
        self.assertEqual(user_response.role, "owner")  # Default value
        self.assertFalse(user_response.email_verified)  # Default value
    
    def test_user_session_model(self):
        """Test user session model."""
        session_id = uuid4()
        user_id = uuid4()
        now = datetime.utcnow()
        
        session = UserSession(
            id=session_id,
            user_id=user_id,
            refresh_token="refresh_token_here",
            device_info="Mozilla/5.0...",
            ip_address="192.168.1.1",
            expires_at=now,
            is_active=True,
            created_at=now
        )
        
        self.assertEqual(session.id, session_id)
        self.assertEqual(session.user_id, user_id)
        self.assertTrue(session.is_active)
    
    def test_jwt_payload_model(self):
        """Test JWT payload model."""
        payload = JWTPayload(
            sub="user-uuid",
            email="test@example.com",
            tenant_id="tenant-uuid",
            role="owner",
            iat=1640000000,
            exp=1640003600
        )
        
        self.assertEqual(payload.sub, "user-uuid")
        self.assertEqual(payload.email, "test@example.com")
        self.assertEqual(payload.role, "owner")
    
    def test_token_pair_model(self):
        """Test token pair model."""
        tokens = TokenPair(
            access_token="jwt.access.token",
            refresh_token="refresh_token_string",
            expires_in=3600,
            token_type="bearer"
        )
        
        self.assertEqual(tokens.access_token, "jwt.access.token")
        self.assertEqual(tokens.refresh_token, "refresh_token_string")
        self.assertEqual(tokens.expires_in, 3600)
        self.assertEqual(tokens.token_type, "bearer")
    
    def test_refresh_token_request(self):
        """Test refresh token request model."""
        request = RefreshTokenRequest(
            refresh_token="refresh_token_here"
        )
        
        self.assertEqual(request.refresh_token, "refresh_token_here")
    
    def test_token_validation_request(self):
        """Test token validation request model."""
        request = TokenValidationRequest(
            token="jwt.token.here"
        )
        
        self.assertEqual(request.token, "jwt.token.here")


class TestResponseModels(unittest.TestCase):
    """Test API response models."""
    
    def test_error_code_enum(self):
        """Test error code enumeration."""
        # Test that all expected error codes exist
        expected_codes = [
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
        
        for code in expected_codes:
            self.assertTrue(hasattr(ErrorCode, code))
            self.assertEqual(getattr(ErrorCode, code).value, code)
    
    def test_error_detail_model(self):
        """Test error detail model."""
        error = ErrorDetail(
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Invalid email or password",
            details={"attempt_count": 1}
        )
        
        self.assertEqual(error.code, ErrorCode.INVALID_CREDENTIALS)
        self.assertEqual(error.message, "Invalid email or password")
        self.assertEqual(error.details["attempt_count"], 1)
    
    def test_api_response_base(self):
        """Test base API response model."""
        response = ApiResponse(
            success=True,
            message="Operation successful"
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Operation successful")
        self.assertIsInstance(response.timestamp, datetime)
    
    def test_success_response_model(self):
        """Test success response model."""
        data = {"user_id": "123"}
        response = SuccessResponse(
            data=data,
            message="User created"
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.data, data)
        self.assertEqual(response.message, "User created")
    
    def test_error_response_model(self):
        """Test error response model."""
        error_detail = ErrorDetail(
            code=ErrorCode.USER_NOT_FOUND,
            message="User not found"
        )
        
        response = ErrorResponse(
            error=error_detail
        )
        
        self.assertFalse(response.success)
        self.assertEqual(response.error.code, ErrorCode.USER_NOT_FOUND)
    
    def test_success_response_helper(self):
        """Test success response helper function."""
        data = {"test": "data"}
        response = success_response(data, "Success message")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["data"], data)
        self.assertEqual(response["message"], "Success message")
        self.assertIn("timestamp", response)
    
    def test_error_response_helper(self):
        """Test error response helper function."""
        response = error_response(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed",
            {"field": "email"}
        )
        
        self.assertFalse(response["success"])
        self.assertEqual(response["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(response["error"]["message"], "Validation failed")
        self.assertEqual(response["error"]["details"]["field"], "email")
        self.assertIn("timestamp", response)
    
    def test_auth_success_response_helper(self):
        """Test authentication success response helper."""
        user_response = UserResponse(
            id=uuid4(),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            created_at=datetime.utcnow()
        )
        
        tokens = TokenPair(
            access_token="jwt.token",
            refresh_token="refresh.token",
            expires_in=3600,
            token_type="bearer"
        )
        
        response = auth_success_response(user_response, tokens, "Login successful")
        
        self.assertTrue(response["success"])
        self.assertEqual(response["message"], "Login successful")
        self.assertIn("user", response)
        self.assertIn("tokens", response)
        self.assertIn("timestamp", response)


class TestModelValidation(unittest.TestCase):
    """Test model validation edge cases."""
    
    def test_empty_string_validation(self):
        """Test validation with empty strings."""
        with self.assertRaises(ValidationError):
            UserRegistration(
                email="",  # Empty email
                password="password123",
                first_name="John",
                last_name="Doe",
                business_name="Test Business"
            )
    
    def test_name_length_validation(self):
        """Test name length validation."""
        # Test maximum length
        long_name = "a" * 101  # Exceeds max length of 100
        
        with self.assertRaises(ValidationError):
            UserRegistration(
                email="test@example.com",
                password="password123",
                first_name=long_name,
                last_name="Doe",
                business_name="Test Business"
            )
    
    def test_user_role_validation(self):
        """Test user role validation."""
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
    
    def test_uuid_field_validation(self):
        """Test UUID field validation."""
        valid_uuid = uuid4()
        
        user = User(
            id=valid_uuid,
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            role="owner",
            email_verified=False,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.assertEqual(user.id, valid_uuid)
    
    def test_optional_fields(self):
        """Test optional field handling."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            first_name="John",
            last_name="Doe",
            role="owner",
            email_verified=False,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
            # tenant_id and last_login_at are optional (None)
        )
        
        self.assertIsNone(user.tenant_id)
        self.assertIsNone(user.last_login_at)


if __name__ == "__main__":
    unittest.main()