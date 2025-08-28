"""
Configuration settings for NeverMissCall shared library.

Provides configuration models and functions following the patterns
defined in the documentation and authentication standards.
"""

import os
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

# Service ports mapping from CLAUDE.md and documentation
SERVICE_PORTS: Dict[str, int] = {
    'auth-service': 3301,
    'tenant-service': 3302,
    'user-service': 3303,
    'config-service': 3304,
    'call-service': 3305,
    'alerts-service': 3101,
    'analytics-service': 3102,
    'provisioning-service': 3501,
    'connection-service': 3105,
    'infrastructure-service': 3106,
    'web-ui': 3000,
    'twilio-service': 3701,
    'ai-service': 3801,
    'calendar-service': 3901,
}

# Service name type for type safety
ServiceName = Literal[
    'auth-service', 'tenant-service', 'user-service', 'config-service',
    'call-service', 'alerts-service', 'analytics-service', 'provisioning-service',
    'connection-service', 'infrastructure-service', 'web-ui', 'twilio-service',
    'ai-service', 'calendar-service'
]


class DatabaseConfigSection(BaseModel):
    """Database configuration section."""
    url: str
    max_connections: int


class JwtConfigSection(BaseModel):
    """JWT configuration section."""
    secret: str
    expires_in: str


class ServiceAuthConfigSection(BaseModel):
    """Service-to-service authentication configuration."""
    key: str


class CommonConfig(BaseModel):
    """
    Common configuration model for all NeverMissCall services.
    
    Follows the configuration patterns defined in the documentation
    with sensible defaults for Phase 1 deployment.
    """
    python_env: str
    log_level: str
    database: DatabaseConfigSection
    jwt: JwtConfigSection
    service_auth: ServiceAuthConfigSection
    
    class Config:
        """Pydantic configuration."""
        env_prefix = ""
        case_sensitive = False


def get_common_config() -> CommonConfig:
    """
    Get common configuration from environment variables.
    
    Uses the environment variables and defaults defined in the
    documentation and authentication standards.
    
    Returns:
        CommonConfig object with all settings
    """
    # Get database URL with fallback construction
    database_url = os.getenv(
        'DATABASE_URL',
        'postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall'
    )
    
    # JWT secret with secure default
    jwt_secret = os.getenv(
        'JWT_SECRET',
        'e8a3b5c7d9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6'
    )
    
    # Service auth key from authentication-standards.md
    service_key = os.getenv(
        'INTERNAL_SERVICE_KEY',
        'nmc-internal-services-auth-key-phase1'
    )
    
    return CommonConfig(
        python_env=os.getenv('PYTHON_ENV', 'development'),
        log_level=os.getenv('LOG_LEVEL', 'debug'),
        database=DatabaseConfigSection(
            url=database_url,
            max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '5'))
        ),
        jwt=JwtConfigSection(
            secret=jwt_secret,
            expires_in=os.getenv('JWT_EXPIRES_IN', '24h')
        ),
        service_auth=ServiceAuthConfigSection(
            key=service_key
        )
    )


def get_service_config(service_name: str, service_specific_config: Any) -> Dict[str, Any]:
    """
    Get service-specific configuration merged with common config.
    
    Args:
        service_name: Name of the service
        service_specific_config: Service-specific configuration object
        
    Returns:
        Merged configuration dictionary
    """
    common = get_common_config()
    
    # Convert common config to dict
    common_dict = common.dict()
    
    # Add service-specific fields
    common_dict['service_name'] = service_name
    common_dict['service_port'] = SERVICE_PORTS.get(service_name, 8000)
    
    # Merge with service-specific config
    if hasattr(service_specific_config, 'dict'):
        common_dict.update(service_specific_config.dict())
    elif isinstance(service_specific_config, dict):
        common_dict.update(service_specific_config)
    
    return common_dict


def get_service_url(service_name: str, host: Optional[str] = None) -> str:
    """
    Get service URL by name.
    
    Args:
        service_name: Name of the service from ServiceName literal
        host: Optional host override (default: localhost)
        
    Returns:
        Full service URL
        
    Raises:
        ValueError: If service name not found in SERVICE_PORTS
    """
    if service_name not in SERVICE_PORTS:
        raise ValueError(f"Unknown service: {service_name}")
    
    host = host or 'localhost'
    port = SERVICE_PORTS[service_name]
    
    return f"http://{host}:{port}"


# Environment variable validation helpers
def validate_required_env_vars() -> Dict[str, str]:
    """
    Validate that all required environment variables are set.
    
    Returns:
        Dictionary of missing environment variables and their descriptions
    """
    required_vars = {
        'DATABASE_URL': 'PostgreSQL connection string',
        'JWT_SECRET': 'JWT signing secret key',
        'INTERNAL_SERVICE_KEY': 'Service-to-service authentication key'
    }
    
    missing = {}
    
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing[var] = description
    
    return missing


def get_environment_info() -> Dict[str, Any]:
    """
    Get current environment information for debugging.
    
    Returns:
        Dictionary with environment details
    """
    config = get_common_config()
    
    return {
        'python_env': config.python_env,
        'log_level': config.log_level,
        'database_configured': bool(config.database.url),
        'jwt_configured': bool(config.jwt.secret),
        'service_auth_configured': bool(config.service_auth.key),
        'available_services': list(SERVICE_PORTS.keys()),
        'missing_env_vars': validate_required_env_vars()
    }