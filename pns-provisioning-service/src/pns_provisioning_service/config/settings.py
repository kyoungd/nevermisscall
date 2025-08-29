"""Configuration settings for pns-provisioning-service."""

import os
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings for pns-provisioning-service."""
    
    # Service Configuration
    service_name: str = Field(default="pns-provisioning-service")
    port: int = Field(default=3501)
    environment: str = Field(default="development")
    log_level: str = Field(default="info")
    version: str = Field(default="1.0.0")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://user:pass@localhost:5432/nevermisscall"
    )
    database_pool_size: int = Field(default=5)
    database_pool_max: int = Field(default=10)
    
    # Twilio Configuration
    twilio_account_sid: str = Field(default="")
    twilio_auth_token: str = Field(default="")
    twilio_api_version: str = Field(default="2010-04-01")
    
    # Webhook Configuration
    webhook_base_url: str = Field(default="https://api.nevermisscall.com")
    webhook_voice_path: str = Field(default="/webhooks/twilio/call")
    webhook_sms_path: str = Field(default="/webhooks/twilio/sms")
    webhook_status_path: str = Field(default="/webhooks/twilio/call/status")
    
    # Authentication
    internal_service_key: str = Field(default="nmc-internal-services-auth-key-phase1")
    jwt_secret_key: str = Field(default="your-secret-key")
    jwt_algorithm: str = Field(default="HS256")
    
    # Service Limits
    max_concurrent_provisioning: int = Field(default=5)
    provisioning_timeout_seconds: int = Field(default=30)
    
    # Cost Protection
    monthly_price_cents_limit: int = Field(default=200)  # $2.00 max per number
    setup_price_cents_limit: int = Field(default=100)    # $1.00 max setup
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_webhook_configuration(settings: Settings) -> Dict[str, Any]:
    """Get webhook URLs configuration."""
    return {
        'voice': {
            'url': f"{settings.webhook_base_url}{settings.webhook_voice_path}",
            'method': 'POST',
            'status_callback': f"{settings.webhook_base_url}{settings.webhook_status_path}"
        },
        'sms': {
            'url': f"{settings.webhook_base_url}{settings.webhook_sms_path}",
            'method': 'POST'
        }
    }


# Global settings instance
settings = Settings()

# Webhook configuration
WEBHOOK_CONFIG = get_webhook_configuration(settings)

# Supported area codes for Phase 1 (major US cities)
SUPPORTED_AREA_CODES = [
    "213", "323", "424", "747", "818",  # Los Angeles
    "212", "646", "917", "347", "929",  # New York
    "415", "628",                       # San Francisco
    "312", "773", "872",               # Chicago
    "713", "281", "832", "346",        # Houston
    "602", "623", "480", "520",        # Phoenix
    "215", "267", "445",               # Philadelphia
    "210", "726", "830",               # San Antonio
    "619", "858", "760", "442",        # San Diego
    "214", "469", "972", "945",        # Dallas
]

# Phone number capabilities
REQUIRED_CAPABILITIES = ["voice", "sms"]