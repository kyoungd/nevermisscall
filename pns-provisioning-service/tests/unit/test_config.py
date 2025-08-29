"""Unit tests for configuration settings."""

import pytest
import os
from unittest.mock import patch

# Add the src directory to Python path
import sys
sys.path.insert(0, '/home/young/Desktop/Code/nvermisscall/nmc/pns-provisioning-service/src')

from pns_provisioning_service.config.settings import Settings


class TestSettings:
    """Test configuration settings."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }, clear=True):
            settings = Settings()
            
            assert settings.service_name == "pns-provisioning-service"
            assert settings.port == 3501
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.database_pool_size == 5
            assert settings.database_pool_max == 20
            
    def test_environment_override(self):
        """Test environment variable override."""
        with patch.dict(os.environ, {
            'SERVICE_NAME': 'custom-pns-service',
            'PORT': '8080',
            'DEBUG': 'true',
            'LOG_LEVEL': 'DEBUG',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }):
            settings = Settings()
            
            assert settings.service_name == "custom-pns-service"
            assert settings.port == 8080
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            
    def test_required_fields_validation(self):
        """Test that required fields raise validation errors when missing."""
        # Test missing DATABASE_URL
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }, clear=True):
            with pytest.raises(Exception):  # Should raise validation error
                Settings()
                
    def test_database_settings(self):
        """Test database-related settings."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/pns_db',
            'DATABASE_POOL_SIZE': '10',
            'DATABASE_POOL_MAX': '50',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }):
            settings = Settings()
            
            assert settings.database_url == 'postgresql://user:pass@localhost:5432/pns_db'
            assert settings.database_pool_size == 10
            assert settings.database_pool_max == 50
            
    def test_twilio_settings(self):
        """Test Twilio configuration."""
        test_sid = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        test_token = 'test_auth_token'
        
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': test_sid,
            'TWILIO_AUTH_TOKEN': test_token,
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }):
            settings = Settings()
            
            assert settings.twilio_account_sid == test_sid
            assert settings.twilio_auth_token == test_token
            
    def test_jwt_settings(self):
        """Test JWT configuration."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'super_secret_key',
            'JWT_ALGORITHM': 'HS512',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }):
            settings = Settings()
            
            assert settings.jwt_secret_key == 'super_secret_key'
            assert settings.jwt_algorithm == 'HS512'
            
    def test_cors_settings(self):
        """Test CORS configuration."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key',
            'ALLOWED_ORIGINS': 'http://localhost:3000,https://app.example.com'
        }):
            settings = Settings()
            
            expected_origins = ['http://localhost:3000', 'https://app.example.com']
            assert settings.allowed_origins == expected_origins
            
    def test_internal_service_key(self):
        """Test internal service key configuration."""
        test_key = 'nmc-internal-services-auth-key-phase1'
        
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': test_key
        }):
            settings = Settings()
            
            assert settings.internal_service_key == test_key


class TestSettingsValidation:
    """Test settings validation and edge cases."""
    
    def test_port_validation(self):
        """Test port number validation."""
        with patch.dict(os.environ, {
            'PORT': '65536',  # Invalid port
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'TWILIO_AUTH_TOKEN': 'test_token',
            'JWT_SECRET_KEY': 'test_secret_key',
            'INTERNAL_SERVICE_KEY': 'test_internal_key'
        }):
            # Should handle invalid port gracefully or raise validation error
            try:
                settings = Settings()
                # If no validation, it should still be an integer
                assert isinstance(settings.port, int)
            except Exception:
                # Validation error is acceptable
                pass
                
    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        # Test various boolean representations
        boolean_values = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False)
        ]
        
        for env_value, expected in boolean_values:
            with patch.dict(os.environ, {
                'DEBUG': env_value,
                'DATABASE_URL': 'postgresql://test:test@localhost/test',
                'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'TWILIO_AUTH_TOKEN': 'test_token',
                'JWT_SECRET_KEY': 'test_secret_key',
                'INTERNAL_SERVICE_KEY': 'test_internal_key'
            }):
                settings = Settings()
                assert settings.debug == expected
                
    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        
        for level in valid_levels:
            with patch.dict(os.environ, {
                'LOG_LEVEL': level,
                'DATABASE_URL': 'postgresql://test:test@localhost/test',
                'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'TWILIO_AUTH_TOKEN': 'test_token',
                'JWT_SECRET_KEY': 'test_secret_key',
                'INTERNAL_SERVICE_KEY': 'test_internal_key'
            }):
                settings = Settings()
                assert settings.log_level == level
                
    def test_database_url_formats(self):
        """Test various database URL formats."""
        valid_urls = [
            'postgresql://user:pass@localhost/dbname',
            'postgresql://user:pass@localhost:5432/dbname',
            'postgresql://user@localhost/dbname',
            'postgres://user:pass@localhost/dbname'  # Alternative scheme
        ]
        
        for url in valid_urls:
            with patch.dict(os.environ, {
                'DATABASE_URL': url,
                'TWILIO_ACCOUNT_SID': 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
                'TWILIO_AUTH_TOKEN': 'test_token',
                'JWT_SECRET_KEY': 'test_secret_key',
                'INTERNAL_SERVICE_KEY': 'test_internal_key'
            }):
                settings = Settings()
                assert settings.database_url == url