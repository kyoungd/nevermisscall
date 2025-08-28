"""
Configuration module for NeverMissCall shared library.

Provides common configuration management, service ports mapping,
and environment variable handling for all microservices.
"""

from .settings import (
    CommonConfig,
    DatabaseConfigSection,
    JwtConfigSection,
    ServiceAuthConfigSection,
    SERVICE_PORTS,
    ServiceName,
    get_common_config,
    get_service_config,
    get_service_url,
    validate_required_env_vars,
    get_environment_info
)

__all__ = [
    "CommonConfig",
    "DatabaseConfigSection", 
    "JwtConfigSection",
    "ServiceAuthConfigSection",
    "SERVICE_PORTS",
    "ServiceName",
    "get_common_config",
    "get_service_config",
    "get_service_url",
    "validate_required_env_vars",
    "get_environment_info"
]