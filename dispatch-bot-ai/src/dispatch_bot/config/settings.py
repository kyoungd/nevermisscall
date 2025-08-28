"""
Application settings and configuration management.
Uses pydantic-settings for environment variable handling.
"""

from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    """Database configuration settings."""
    url: str = Field(default="sqlite:///./dispatch_bot.db", description="Database URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=5, description="Connection pool size")


class LoggingSettings(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO", description="Log level")
    json_logs: bool = Field(default=True, description="Use JSON logging format")
    log_file: Optional[str] = Field(default=None, description="Optional log file path")


class APISettings(BaseModel):
    """API configuration settings."""
    title: str = Field(default="Dispatch Bot AI API", description="API title")
    description: str = Field(
        default="AI-powered scheduling and response platform for field service professionals",
        description="API description"
    )
    version: str = Field(default="1.0.0", description="API version")
    debug: bool = Field(default=False, description="Enable debug mode")
    docs_url: Optional[str] = Field(default="/docs", description="Documentation URL")
    redoc_url: Optional[str] = Field(default="/redoc", description="ReDoc URL")


class SecuritySettings(BaseModel):
    """Security configuration settings."""
    api_key_header: str = Field(default="Authorization", description="API key header name")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"],
        description="Allowed CORS methods"
    )


class ExternalServicesSettings(BaseModel):
    """External service configuration settings."""
    geocoding_api_key: Optional[str] = Field(default=None, description="Geocoding service API key")
    traffic_api_key: Optional[str] = Field(default=None, description="Traffic service API key")
    llm_api_key: Optional[str] = Field(default=None, description="LLM service API key")
    
    # Service URLs
    geocoding_base_url: str = Field(
        default="https://api.geocoding-service.com",
        description="Geocoding service base URL"
    )
    traffic_base_url: str = Field(
        default="https://api.traffic-service.com",
        description="Traffic service base URL"
    )
    llm_base_url: str = Field(
        default="https://api.llm-service.com",
        description="LLM service base URL"
    )


class Settings(BaseSettings):
    """
    Main application settings.
    
    Settings can be configured via environment variables with DISPATCH_BOT_ prefix.
    For nested settings, use double underscores: DISPATCH_BOT_DATABASE__URL
    """
    
    model_config = SettingsConfigDict(
        env_prefix="DISPATCH_BOT_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    environment: str = Field(default="development", description="Environment (development/production/test)")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    
    # Nested configuration objects
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    external_services: ExternalServicesSettings = Field(default_factory=ExternalServicesSettings)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.environment.lower() == "test"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get the current settings instance.
    
    This function can be overridden in tests to provide test-specific settings.
    """
    return settings