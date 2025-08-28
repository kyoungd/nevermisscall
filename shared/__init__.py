"""
NeverMissCall Shared Library

Provides common utilities, database access, configuration management, 
and models for all NeverMissCall microservices.
"""

# Core database functions
from .database import (
    SimpleDatabase,
    DatabaseConfig,
    init_database,
    get_database,
    query,
    health_check,
    database
)

# Configuration functions
from .config import (
    CommonConfig,
    get_common_config,
    get_service_config,
    get_service_url,
    SERVICE_PORTS
)

# Utility functions
from .utils import (
    logger,
    ServiceClient,
    validate_required,
    validate_email,
    validate_phone_number,
    validate_uuid,
    validate_password,
    format_date,
    is_valid_date,
    sanitize_string,
    generate_id,
    async_handler,
    require_service_auth
)

# Response helpers
from .models import (
    ApiResponse,
    success_response,
    error_response,
    HealthStatus,
    User,
    Tenant,
    Call,
    JwtPayload,
    ValidationError,
    NotFoundError,
    UnauthorizedError
)

__version__ = "1.0.0"
__all__ = [
    # Database
    "SimpleDatabase",
    "DatabaseConfig", 
    "init_database",
    "get_database",
    "query",
    "health_check",
    "database",
    
    # Configuration
    "CommonConfig",
    "get_common_config", 
    "get_service_config",
    "get_service_url",
    "SERVICE_PORTS",
    
    # Utilities
    "logger",
    "ServiceClient",
    "validate_required",
    "validate_email", 
    "validate_phone_number",
    "validate_uuid",
    "validate_password",
    "format_date",
    "is_valid_date", 
    "sanitize_string",
    "generate_id",
    "async_handler",
    "require_service_auth",
    
    # Models and responses
    "ApiResponse",
    "success_response",
    "error_response", 
    "HealthStatus",
    "User",
    "Tenant",
    "Call", 
    "JwtPayload",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError"
]