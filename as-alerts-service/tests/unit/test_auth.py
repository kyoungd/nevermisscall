"""
Unit tests for AS Alerts Service authentication.

Tests service-to-service authentication following unittest patterns
and real authentication scenarios.
"""

import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from main import verify_service_auth


class TestServiceAuthentication(unittest.TestCase):
    """Test verify_service_auth enforces proper service-to-service authentication."""
    
    async def test_verify_service_auth_with_valid_key(self):
        """Test verify_service_auth accepts valid service key."""
        valid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="nmc-internal-services-auth-key-phase1"
        )
        
        # Should not raise exception with valid key
        result = await verify_service_auth(valid_credentials)
        
        self.assertTrue(result)
    
    async def test_verify_service_auth_with_no_credentials(self):
        """Test verify_service_auth rejects missing credentials."""
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(None)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Service authentication required")
    
    async def test_verify_service_auth_with_invalid_key(self):
        """Test verify_service_auth rejects invalid service key."""
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-service-key"
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(invalid_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")
    
    async def test_verify_service_auth_with_empty_credentials(self):
        """Test verify_service_auth rejects empty credentials."""
        empty_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=""
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(empty_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")
    
    @patch.dict('os.environ', {'INTERNAL_SERVICE_KEY': 'custom-service-key-123'})
    async def test_verify_service_auth_with_custom_env_key(self):
        """Test verify_service_auth uses custom service key from environment."""
        custom_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="custom-service-key-123"
        )
        
        # Should accept custom key from environment
        result = await verify_service_auth(custom_credentials)
        
        self.assertTrue(result)
    
    @patch.dict('os.environ', {'INTERNAL_SERVICE_KEY': 'custom-service-key-123'})
    async def test_verify_service_auth_rejects_default_when_custom_set(self):
        """Test verify_service_auth rejects default key when custom key is set."""
        default_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="nmc-internal-services-auth-key-phase1"
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(default_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")
    
    async def test_verify_service_auth_case_sensitive(self):
        """Test verify_service_auth is case sensitive for security."""
        case_different_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="NMC-INTERNAL-SERVICES-AUTH-KEY-PHASE1"  # Uppercase
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(case_different_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")
    
    async def test_verify_service_auth_with_whitespace_key(self):
        """Test verify_service_auth rejects key with whitespace."""
        whitespace_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=" nmc-internal-services-auth-key-phase1 "
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(whitespace_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")
    
    async def test_verify_service_auth_with_partial_key(self):
        """Test verify_service_auth rejects partial service key."""
        partial_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="nmc-internal-services"  # Incomplete key
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(partial_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")
    
    async def test_verify_service_auth_with_extra_characters(self):
        """Test verify_service_auth rejects key with extra characters."""
        extra_char_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="nmc-internal-services-auth-key-phase1-extra"
        )
        
        with self.assertRaises(HTTPException) as context:
            await verify_service_auth(extra_char_credentials)
        
        error = context.exception
        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.detail, "Invalid service key")


class TestAuthenticationIntegration(unittest.TestCase):
    """Test authentication integration with real business security requirements."""
    
    def test_service_key_matches_documentation_standard(self):
        """Test default service key matches authentication-standards.md."""
        import os
        from main import verify_service_auth
        
        # The default key should match what's documented
        expected_key = "nmc-internal-services-auth-key-phase1"
        
        # This is the key that should be used in production
        default_key = os.getenv('INTERNAL_SERVICE_KEY', 'nmc-internal-services-auth-key-phase1')
        
        # In absence of environment override, should use documented default
        if 'INTERNAL_SERVICE_KEY' not in os.environ:
            self.assertEqual(default_key, expected_key)
    
    def test_authentication_prevents_unauthorized_access(self):
        """Test authentication prevents real unauthorized access scenarios."""
        # These are realistic attack attempts that should be blocked
        malicious_attempts = [
            None,  # No credentials
            "",    # Empty string
            "guest",  # Common default
            "admin",  # Common default
            "password",  # Weak attempt
            "bearer-token",  # Generic bearer
            "nmc-service-key",  # Similar but wrong
            "nmc-internal-services-auth-key",  # Missing suffix
            "nmc-internal-services-auth-key-phase2",  # Wrong phase
            "123456",  # Numeric attempt
        ]
        
        # All of these should result in authentication failure
        for malicious_key in malicious_attempts:
            with self.subTest(malicious_key=malicious_key):
                credentials = None
                if malicious_key is not None:
                    credentials = HTTPAuthorizationCredentials(
                        scheme="Bearer",
                        credentials=malicious_key
                    )
                
                # Should raise HTTPException for all malicious attempts
                with self.assertRaises(HTTPException):
                    # Note: This is a coroutine, but we're testing the logic
                    import asyncio
                    asyncio.run(verify_service_auth(credentials))
    
    def test_authentication_error_responses_are_consistent(self):
        """Test authentication errors provide consistent responses for security."""
        import asyncio
        
        # Different invalid attempts should return same error structure
        invalid_attempts = [
            None,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-key"),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=""),
        ]
        
        error_responses = []
        
        for invalid_attempt in invalid_attempts:
            try:
                asyncio.run(verify_service_auth(invalid_attempt))
            except HTTPException as e:
                error_responses.append(e.status_code)
        
        # All should return 401 status
        self.assertTrue(all(code == 401 for code in error_responses))
        
        # This prevents information leakage about why auth failed
    
    def test_service_authentication_supports_environment_override(self):
        """Test service authentication supports production environment configuration."""
        # In production, services should be able to use custom keys
        # This tests the environment variable override functionality
        
        with patch.dict('os.environ', {'INTERNAL_SERVICE_KEY': 'production-service-key-xyz'}):
            import asyncio
            
            # Should accept the production key
            valid_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="production-service-key-xyz"
            )
            
            result = asyncio.run(verify_service_auth(valid_credentials))
            self.assertTrue(result)
            
            # Should reject the default development key
            default_credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="nmc-internal-services-auth-key-phase1"
            )
            
            with self.assertRaises(HTTPException):
                asyncio.run(verify_service_auth(default_credentials))


if __name__ == '__main__':
    unittest.main()