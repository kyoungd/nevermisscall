"""Configuration settings for ts-auth-service."""

import os
from typing import List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service Configuration
    service_name: str = Field(default="ts-auth-service")
    port: int = Field(default=3301)
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    version: str = Field(default="1.0.0")
    
    # Database Configuration
    database_url: str = Field(..., description="PostgreSQL connection string")
    database_pool_min: int = Field(default=2)
    database_pool_max: int = Field(default=10)
    database_timeout: int = Field(default=30)
    
    # JWT Configuration  
    jwt_secret: str = Field(..., description="JWT signing secret key")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_in: int = Field(default=3600, description="Access token expiry in seconds")
    refresh_token_expires_in: int = Field(default=2592000, description="Refresh token expiry in seconds (30 days)")
    
    # Password & Security
    bcrypt_salt_rounds: int = Field(default=12)
    password_min_length: int = Field(default=8)
    
    # Rate Limiting
    rate_limit_window_ms: int = Field(default=60000, description="Rate limit window in milliseconds")
    rate_limit_max_requests: int = Field(default=10, description="Max requests per window")
    
    # CORS Configuration
    allowed_origins: List[str] = Field(default=["http://localhost:3000"], description="Allowed CORS origins")
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = Field(default=["*"])
    
    # Internal Service Authentication
    internal_service_key: str = Field(default="nmc-internal-services-auth-key-phase1")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    
    url: str
    pool_min: int = 2
    pool_max: int = 10
    timeout: int = 30
    
    @classmethod
    def from_settings(cls, settings: Settings) -> "DatabaseConfig":
        return cls(
            url=settings.database_url,
            pool_min=settings.database_pool_min,
            pool_max=settings.database_pool_max,
            timeout=settings.database_timeout
        )


class JWTConfig(BaseModel):
    """JWT token configuration."""
    
    secret: str
    algorithm: str = "HS256"
    access_token_expire: int = 3600
    refresh_token_expire: int = 2592000
    
    @classmethod
    def from_settings(cls, settings: Settings) -> "JWTConfig":
        return cls(
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            access_token_expire=settings.jwt_expires_in,
            refresh_token_expire=settings.refresh_token_expires_in
        )


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    bcrypt_rounds: int = 12
    password_min_length: int = 8
    rate_limit_window: int = 60000
    rate_limit_max: int = 10
    
    @classmethod
    def from_settings(cls, settings: Settings) -> "SecurityConfig":
        return cls(
            bcrypt_rounds=settings.bcrypt_salt_rounds,
            password_min_length=settings.password_min_length,
            rate_limit_window=settings.rate_limit_window_ms,
            rate_limit_max=settings.rate_limit_max_requests
        )


# Global settings instance
settings = Settings()

# Configuration instances
database_config = DatabaseConfig.from_settings(settings)
jwt_config = JWTConfig.from_settings(settings)
security_config = SecurityConfig.from_settings(settings)