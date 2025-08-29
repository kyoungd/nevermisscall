"""Configuration settings for as-infrastructure-service."""

import os
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings for as-infrastructure-service."""
    
    # Service Configuration
    service_name: str = Field(default="as-infrastructure-service")
    port: int = Field(default=3106)
    environment: str = Field(default="development")
    log_level: str = Field(default="info")
    version: str = Field(default="1.0.0")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379")
    metrics_redis_db: int = Field(default=3)
    health_data_ttl_seconds: int = Field(default=86400)  # 24 hours
    
    # Health Check Configuration
    default_check_interval_ms: int = Field(default=30000)  # 30 seconds
    critical_service_check_interval_ms: int = Field(default=15000)  # 15 seconds
    health_check_timeout_ms: int = Field(default=5000)  # 5 seconds
    max_consecutive_failures: int = Field(default=5)
    
    # Alert Configuration
    alert_check_interval_ms: int = Field(default=60000)  # 1 minute
    alert_cooldown_minutes: int = Field(default=5)
    enable_email_alerts: bool = Field(default=False)
    enable_slack_alerts: bool = Field(default=False)
    
    # Authentication
    internal_service_key: str = Field(default="nmc-internal-services-auth-key-phase1")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Service Registry Configuration
SERVICE_REGISTRY = {
    'ts-auth-service': {
        'url': 'http://localhost:3301',
        'health_endpoint': '/health',
        'check_interval': 30000,  # 30 seconds
        'timeout': 5000,
        'critical': False,
        'category': 'identity'
    },
    'ts-tenant-service': {
        'url': 'http://localhost:3302', 
        'health_endpoint': '/health',
        'check_interval': 30000,
        'timeout': 5000,
        'critical': False,
        'category': 'identity'
    },
    'ts-user-service': {
        'url': 'http://localhost:3303',
        'health_endpoint': '/health',
        'check_interval': 30000,
        'timeout': 5000,
        'critical': False,
        'category': 'identity'
    },
    'as-call-service': {
        'url': 'http://localhost:3103',
        'health_endpoint': '/health', 
        'check_interval': 15000,  # 15 seconds - critical service
        'timeout': 3000,
        'critical': True,
        'category': 'core'
    },
    'as-connection-service': {
        'url': 'http://localhost:3105',
        'health_endpoint': '/health',
        'check_interval': 15000,
        'timeout': 3000,
        'critical': True,
        'category': 'core'
    },
    'pns-provisioning-service': {
        'url': 'http://localhost:3501',
        'health_endpoint': '/health',
        'check_interval': 30000,
        'timeout': 5000,
        'critical': False,
        'category': 'external'
    },
    'twilio-server': {
        'url': 'http://localhost:3701',
        'health_endpoint': '/health',
        'check_interval': 15000,
        'timeout': 3000,
        'critical': True,
        'category': 'external'
    },
    'dispatch-bot-ai': {
        'url': 'http://localhost:3801',
        'health_endpoint': '/health',
        'check_interval': 15000, 
        'timeout': 5000,
        'critical': True,
        'category': 'external'
    },
    'web-ui': {
        'url': 'http://localhost:3000',
        'health_endpoint': '/api/health',
        'check_interval': 30000,
        'timeout': 5000,
        'critical': True,
        'category': 'frontend'
    }
}

# Alert Thresholds Configuration
ALERT_THRESHOLDS = {
    'response_time': {
        'warning': 1000,    # 1 second
        'critical': 3000    # 3 seconds  
    },
    'error_rate': {
        'warning': 0.01,    # 1%
        'critical': 0.05    # 5%
    },
    'consecutive_failures': {
        'warning': 2,
        'critical': 5
    },
    'uptime': {
        'warning': 99.0,    # 99%
        'critical': 95.0    # 95%
    }
}

# Service Dependencies Configuration
SERVICE_DEPENDENCIES = {
    'as-call-service': ['ts-auth-service', 'ts-tenant-service', 'twilio-server', 'dispatch-bot-ai'],
    'web-ui': ['ts-auth-service', 'as-call-service', 'as-connection-service'],
    'ts-tenant-service': ['pns-provisioning-service'],
    'as-connection-service': ['ts-auth-service'],
    'dispatch-bot-ai': [],
    'twilio-server': [],
    'ts-auth-service': [],
    'ts-user-service': ['ts-auth-service'],
    'pns-provisioning-service': []
}

# Critical Path Services (failure impacts core functionality)
CRITICAL_PATH_SERVICES = [
    'twilio-server',
    'as-call-service', 
    'as-connection-service',
    'web-ui'
]

# Global settings instance
settings = Settings()