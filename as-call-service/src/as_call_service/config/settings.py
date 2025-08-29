"""Configuration settings for as-call-service."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    test_database_url: Optional[str] = Field(None, env="TEST_DATABASE_URL")
    
    # Service Dependencies
    twilio_server_url: str = Field("http://localhost:3701", env="TWILIO_SERVER_URL")
    dispatch_ai_url: str = Field("http://localhost:3801", env="DISPATCH_AI_URL")
    ts_tenant_service_url: str = Field("http://localhost:3302", env="TS_TENANT_SERVICE_URL")
    as_connection_service_url: str = Field("http://localhost:3105", env="AS_CONNECTION_SERVICE_URL")
    
    # Service Authentication
    internal_service_key: str = Field(..., env="INTERNAL_SERVICE_KEY")
    jwt_secret: Optional[str] = Field(None, env="JWT_SECRET")
    
    # Business Logic Configuration
    ai_takeover_delay_seconds: int = Field(60, env="AI_TAKEOVER_DELAY_SECONDS")
    message_timeout_minutes: int = Field(30, env="MESSAGE_TIMEOUT_MINUTES")
    max_conversation_messages: int = Field(1000, env="MAX_CONVERSATION_MESSAGES")
    service_area_validation_enabled: bool = Field(True, env="SERVICE_AREA_VALIDATION_ENABLED")
    
    # Service Configuration
    port: int = Field(3104, env="PORT")
    host: str = Field("0.0.0.0", env="HOST")
    service_name: str = Field("as-call-service", env="SERVICE_NAME")
    
    # Development Settings
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_json: bool = Field(True, env="LOG_JSON")
    
    # Performance and limits
    max_workers: int = Field(4, env="MAX_WORKERS")
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or os.getenv("ENV", "").lower() in ["dev", "development"]
    
    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins based on environment."""
        if self.is_development:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return []


# Global settings instance
settings = Settings()