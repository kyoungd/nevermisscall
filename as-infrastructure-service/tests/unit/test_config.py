"""Test configuration settings."""

import pytest
import os
from unittest.mock import patch

from src.as_infrastructure_service.config.settings import (
    Settings,
    SERVICE_REGISTRY,
    ALERT_THRESHOLDS,
    SERVICE_DEPENDENCIES,
    CRITICAL_PATH_SERVICES
)


class TestConfiguration:
    """Test application configuration."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        assert settings.service_name == "as-infrastructure-service"
        assert settings.port == 3106
        assert settings.environment == "development"
        assert settings.log_level == "info"
        assert settings.version == "1.0.0"
    
    def test_redis_configuration(self):
        """Test Redis configuration settings."""
        settings = Settings()
        
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.metrics_redis_db == 3
        assert settings.health_data_ttl_seconds == 86400
    
    def test_health_check_configuration(self):
        """Test health check configuration."""
        settings = Settings()
        
        assert settings.default_check_interval_ms == 30000
        assert settings.critical_service_check_interval_ms == 15000
        assert settings.health_check_timeout_ms == 5000
        assert settings.max_consecutive_failures == 5
    
    def test_alert_configuration(self):
        """Test alert configuration."""
        settings = Settings()
        
        assert settings.alert_check_interval_ms == 60000
        assert settings.alert_cooldown_minutes == 5
        assert settings.enable_email_alerts is False
        assert settings.enable_slack_alerts is False
    
    def test_environment_variable_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'PORT': '8080',
            'LOG_LEVEL': 'debug',
            'ENVIRONMENT': 'production'
        }):
            settings = Settings()
            
            assert settings.port == 8080
            assert settings.log_level == 'debug'
            assert settings.environment == 'production'
    
    def test_service_registry_structure(self):
        """Test service registry configuration."""
        assert isinstance(SERVICE_REGISTRY, dict)
        assert len(SERVICE_REGISTRY) > 0
        
        # Check required services are present
        required_services = [
            'ts-auth-service',
            'as-call-service',
            'twilio-server',
            'web-ui'
        ]
        
        for service in required_services:
            assert service in SERVICE_REGISTRY
            config = SERVICE_REGISTRY[service]
            assert 'url' in config
            assert 'health_endpoint' in config
            assert 'check_interval' in config
            assert 'timeout' in config
            assert 'critical' in config
    
    def test_critical_services_configuration(self):
        """Test critical services are properly marked."""
        critical_services = [
            name for name, config in SERVICE_REGISTRY.items()
            if config.get('critical', False)
        ]
        
        # Should have at least core services marked as critical
        expected_critical = ['as-call-service', 'twilio-server', 'web-ui']
        for service in expected_critical:
            assert service in critical_services
    
    def test_alert_thresholds_structure(self):
        """Test alert thresholds configuration."""
        assert isinstance(ALERT_THRESHOLDS, dict)
        
        required_thresholds = [
            'response_time',
            'error_rate',
            'consecutive_failures',
            'uptime'
        ]
        
        for threshold_type in required_thresholds:
            assert threshold_type in ALERT_THRESHOLDS
            
            threshold_config = ALERT_THRESHOLDS[threshold_type]
            assert isinstance(threshold_config, dict)
            
            # Some thresholds should have warning and critical levels
            if threshold_type in ['response_time', 'error_rate', 'uptime']:
                assert 'warning' in threshold_config
                assert 'critical' in threshold_config
    
    def test_service_dependencies_structure(self):
        """Test service dependencies configuration."""
        assert isinstance(SERVICE_DEPENDENCIES, dict)
        
        # Check dependencies are lists
        for service, deps in SERVICE_DEPENDENCIES.items():
            assert isinstance(deps, list)
            
            # Dependencies should reference valid services
            for dep in deps:
                assert dep in SERVICE_REGISTRY or dep == service
    
    def test_critical_path_services(self):
        """Test critical path services configuration."""
        assert isinstance(CRITICAL_PATH_SERVICES, list)
        assert len(CRITICAL_PATH_SERVICES) > 0
        
        # All critical path services should exist in registry
        for service in CRITICAL_PATH_SERVICES:
            assert service in SERVICE_REGISTRY
            
            # Critical path services should be marked as critical
            assert SERVICE_REGISTRY[service]['critical'] is True
    
    def test_service_categories(self):
        """Test service categorization."""
        categories = set()
        for service_config in SERVICE_REGISTRY.values():
            category = service_config.get('category', 'core')
            categories.add(category)
        
        # Should have expected categories
        expected_categories = ['identity', 'core', 'external', 'frontend']
        for category in expected_categories:
            assert category in categories
    
    def test_service_urls_format(self):
        """Test service URL formats."""
        for service_name, config in SERVICE_REGISTRY.items():
            url = config['url']
            
            # Should be proper HTTP URLs
            assert url.startswith('http://') or url.startswith('https://')
            
            # Should have localhost for development
            assert 'localhost' in url
            
            # Should have valid port numbers
            if ':' in url.split('//')[-1]:
                port_part = url.split(':')[-1].split('/')[0]
                port = int(port_part)
                assert 1000 <= port <= 9999
    
    def test_authentication_configuration(self):
        """Test authentication settings."""
        settings = Settings()
        
        assert settings.internal_service_key == "nmc-internal-services-auth-key-phase1"
        assert len(settings.internal_service_key) > 10  # Should be substantial key