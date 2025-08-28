"""
Tests for environment configuration and settings loading.
"""

import pytest
import os
from pathlib import Path
from dispatch_bot.config.phase1_settings import Phase1Settings, get_phase1_settings, validate_environment


class TestEnvironmentConfiguration:
    """Test environment and settings configuration"""
    
    def test_settings_load_from_env_file(self):
        """Test that settings can load from .env file"""
        settings = Phase1Settings()
        
        # Basic settings should load
        assert settings.app_name == "Never Missed Call AI"
        assert settings.app_version == "1.0.0"
        assert isinstance(settings.debug, bool)
        assert settings.log_level in ["debug", "info", "warning", "error"]
    
    def test_google_maps_settings_structure(self):
        """Test Google Maps settings structure"""
        settings = get_phase1_settings()
        
        assert hasattr(settings, 'google_maps')
        assert hasattr(settings.google_maps, 'api_key')
        assert hasattr(settings.google_maps, 'geocoding_url')
        assert hasattr(settings.google_maps, 'distance_matrix_url')
        
        # URLs should be valid
        assert settings.google_maps.geocoding_url.startswith('https://')
        assert settings.google_maps.distance_matrix_url.startswith('https://')
        assert 'googleapis.com' in settings.google_maps.geocoding_url
    
    def test_openai_settings_structure(self):
        """Test OpenAI settings structure"""
        settings = get_phase1_settings()
        
        assert hasattr(settings, 'openai')
        assert hasattr(settings.openai, 'api_key')
        assert hasattr(settings.openai, 'model')
        assert hasattr(settings.openai, 'temperature')
        assert hasattr(settings.openai, 'max_tokens')
        
        # Validate defaults
        assert settings.openai.model == "gpt-4"
        assert 0.0 <= settings.openai.temperature <= 1.0
        assert settings.openai.max_tokens > 0
    
    def test_business_settings_structure(self):
        """Test business settings structure and defaults"""
        settings = get_phase1_settings()
        
        assert hasattr(settings, 'business')
        assert settings.business.default_hours_start == "07:00"
        assert settings.business.default_hours_end == "18:00"
        assert settings.business.default_service_radius_miles == 25
        assert settings.business.default_trade_type == "plumbing"
        assert settings.business.default_job_estimate_min > 0
        assert settings.business.default_job_estimate_max > settings.business.default_job_estimate_min
    
    def test_api_key_validation_properties(self):
        """Test API key validation helper properties"""
        settings = get_phase1_settings()
        
        # These should be boolean values
        assert isinstance(settings.has_google_maps_key, bool)
        assert isinstance(settings.has_openai_key, bool)
    
    def test_validate_required_keys_structure(self):
        """Test API key validation method structure"""
        settings = get_phase1_settings()
        validation = settings.validate_required_keys()
        
        # Should have required structure
        assert "valid" in validation
        assert "missing_keys" in validation
        assert "warnings" in validation
        
        assert isinstance(validation["valid"], bool)
        assert isinstance(validation["missing_keys"], list)
        assert isinstance(validation["warnings"], list)
    
    def test_environment_validation_function(self):
        """Test environment validation function"""
        validation = validate_environment()
        
        assert "environment" in validation
        assert "valid" in validation
        assert "missing_keys" in validation
        
        env_info = validation["environment"]
        assert "app_name" in env_info
        assert "version" in env_info
        assert "debug" in env_info
        assert "log_level" in env_info
    
    def test_settings_defaults_are_reasonable(self):
        """Test that default settings values are reasonable"""
        settings = Phase1Settings()
        
        # Server settings
        assert settings.host in ["0.0.0.0", "127.0.0.1", "localhost"]
        assert 1000 <= settings.port <= 65535
        
        # Rate limiting
        assert settings.rate_limit_per_minute > 0
        assert settings.rate_limit_per_hour > settings.rate_limit_per_minute
        
        # Logging
        assert settings.log_max_size_mb > 0
        assert settings.log_backup_count >= 0


class TestEnvironmentFileHandling:
    """Test handling of .env file and environment variables"""
    
    def test_env_file_exists(self):
        """Test that .env file exists in project root"""
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"
        
        assert env_file.exists(), f".env file should exist at {env_file}"
    
    def test_env_example_file_exists(self):
        """Test that .env.example file exists"""
        project_root = Path(__file__).parent.parent.parent  
        env_example = project_root / ".env.example"
        
        assert env_example.exists(), f".env.example file should exist at {env_example}"
    
    def test_env_files_have_required_keys(self):
        """Test that .env files contain required key placeholders"""
        project_root = Path(__file__).parent.parent.parent
        
        # Check .env.example
        env_example = project_root / ".env.example"
        example_content = env_example.read_text()
        
        required_keys = [
            "GOOGLE_MAPS_API_KEY",
            "OPENAI_API_KEY",
            "APP_NAME",
            "DEBUG",
            "LOG_LEVEL"
        ]
        
        for key in required_keys:
            assert key in example_content, f"{key} should be in .env.example"
        
        # Check .env
        env_file = project_root / ".env"
        env_content = env_file.read_text()
        
        for key in required_keys:
            assert key in env_content, f"{key} should be in .env"


class TestSettingsWithMockEnvironment:
    """Test settings behavior with mocked environment variables"""
    
    def test_settings_with_mock_google_key(self, monkeypatch):
        """Test settings when Google Maps API key is set"""
        test_key = "test_google_maps_key_12345"
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", test_key)
        
        settings = Phase1Settings()
        assert settings.google_maps_api_key == test_key
        assert settings.has_google_maps_key == True
    
    def test_settings_with_mock_openai_key(self, monkeypatch):
        """Test settings when OpenAI API key is set"""
        test_key = "sk-test_openai_key_12345"
        monkeypatch.setenv("OPENAI_API_KEY", test_key)
        
        settings = Phase1Settings()
        assert settings.openai_api_key == test_key
        assert settings.has_openai_key == True
    
    def test_validation_passes_with_both_keys(self, monkeypatch):
        """Test validation passes when both API keys are set"""
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test_google_key")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test_openai_key")
        
        settings = Phase1Settings()
        validation = settings.validate_required_keys()
        
        assert validation["valid"] == True
        assert len(validation["missing_keys"]) == 0
    
    def test_validation_fails_without_keys(self, monkeypatch):
        """Test validation fails when API keys are missing"""
        # Remove any existing keys
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "")
        monkeypatch.setenv("OPENAI_API_KEY", "")
        
        settings = Phase1Settings()
        validation = settings.validate_required_keys()
        
        assert validation["valid"] == False
        assert "GOOGLE_MAPS_API_KEY" in validation["missing_keys"]
        assert "OPENAI_API_KEY" in validation["missing_keys"]
        assert len(validation["warnings"]) > 0