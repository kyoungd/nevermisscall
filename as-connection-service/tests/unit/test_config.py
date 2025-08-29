"""Test configuration settings."""

import pytest
import os
from unittest.mock import patch

from src.as_connection_service.config.settings import Settings, settings


class TestSettings:
    """Test Settings configuration."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        default_settings = Settings()
        
        assert default_settings.service_name == "as-connection-service"
        assert default_settings.port == 3105
        assert default_settings.log_level == "INFO"
        assert default_settings.redis_url == "redis://localhost:6379"
        assert default_settings.connection_redis_db == 1
        assert default_settings.event_queue_redis_db == 2
        assert default_settings.connection_ttl_seconds == 3600
        assert default_settings.socketio_cors_origin == "http://localhost:3000"
        assert default_settings.max_connections_per_tenant == 10
        assert default_settings.max_events_per_minute_per_tenant == 100
        assert default_settings.internal_service_key == "nmc-internal-services-auth-key-phase1"
    
    def test_cors_origins_property(self):
        """Test CORS origins parsing."""
        test_settings = Settings(socketio_cors_origin="http://localhost:3000,https://app.nevermisscall.com")
        
        cors_origins = test_settings.cors_origins
        assert len(cors_origins) == 2
        assert "http://localhost:3000" in cors_origins
        assert "https://app.nevermisscall.com" in cors_origins
    
    def test_transports_property(self):
        """Test Socket.IO transports parsing."""
        test_settings = Settings(socketio_transports="websocket,polling")
        
        transports = test_settings.transports
        assert len(transports) == 2
        assert "websocket" in transports
        assert "polling" in transports
    
    def test_single_cors_origin(self):
        """Test single CORS origin."""
        test_settings = Settings(socketio_cors_origin="http://localhost:3000")
        
        cors_origins = test_settings.cors_origins
        assert len(cors_origins) == 1
        assert cors_origins[0] == "http://localhost:3000"
    
    @patch.dict(os.environ, {
        'PORT': '3500',
        'LOG_LEVEL': 'DEBUG',
        'REDIS_URL': 'redis://test-redis:6379',
        'MAX_CONNECTIONS_PER_TENANT': '20'
    })
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        # Create new settings instance to pick up env vars
        env_settings = Settings()
        
        assert env_settings.port == 3500
        assert env_settings.log_level == "DEBUG"
        assert env_settings.redis_url == "redis://test-redis:6379"
        assert env_settings.max_connections_per_tenant == 20
    
    def test_global_settings_instance(self):
        """Test global settings instance."""
        # Global settings should be accessible
        assert settings.service_name == "as-connection-service"
        assert isinstance(settings.port, int)
        assert isinstance(settings.cors_origins, list)
        assert isinstance(settings.transports, list)
    
    def test_settings_validation(self):
        """Test settings validation."""
        # Valid settings
        valid_settings = Settings(
            port=3105,
            connection_ttl_seconds=3600,
            max_connections_per_tenant=10
        )
        
        assert valid_settings.port == 3105
        assert valid_settings.connection_ttl_seconds == 3600
        assert valid_settings.max_connections_per_tenant == 10
    
    def test_redis_configuration(self):
        """Test Redis-specific configuration."""
        redis_settings = Settings(
            redis_url="redis://custom-redis:6380",
            connection_redis_db=2,
            event_queue_redis_db=3
        )
        
        assert redis_settings.redis_url == "redis://custom-redis:6380"
        assert redis_settings.connection_redis_db == 2
        assert redis_settings.event_queue_redis_db == 3
    
    def test_socketio_configuration(self):
        """Test Socket.IO specific configuration."""
        socketio_settings = Settings(
            heartbeat_interval_ms=15000,
            heartbeat_timeout_ms=30000
        )
        
        assert socketio_settings.heartbeat_interval_ms == 15000
        assert socketio_settings.heartbeat_timeout_ms == 30000