"""Configuration settings for as-connection-service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    service_name: str = "as-connection-service"
    port: int = 3105
    log_level: str = "INFO"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    connection_redis_db: int = 1
    event_queue_redis_db: int = 2
    connection_ttl_seconds: int = 3600
    
    # Socket.IO Configuration
    socketio_cors_origin: str = "http://localhost:3000"
    socketio_transports: str = "websocket,polling"
    heartbeat_interval_ms: int = 30000
    heartbeat_timeout_ms: int = 60000
    
    # Rate Limiting
    max_connections_per_tenant: int = 10
    max_events_per_minute_per_tenant: int = 100
    max_messages_per_minute_per_user: int = 30
    
    # Service Dependencies
    ts_auth_service_url: str = "http://localhost:3301"
    as_call_service_url: str = "http://localhost:3104"
    ts_tenant_service_url: str = "http://localhost:3302"
    
    # Service Authentication
    internal_service_key: str = "nmc-internal-services-auth-key-phase1"
    
    class Config:
        env_file = ".env"
        
    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        return self.socketio_cors_origin.split(',')
        
    @property 
    def transports(self) -> list[str]:
        """Get Socket.IO transports as a list."""
        return self.socketio_transports.split(',')


# Global settings instance
settings = Settings()