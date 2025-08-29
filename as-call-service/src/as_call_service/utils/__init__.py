"""Utilities package for as-call-service."""

from .shared_integration import (
    logger,
    validateRequired,
    successResponse,
    errorResponse,
    ValidationError,
    DatabaseError,
    ServiceError,
    AuthenticationError,
    init_database,
    query,
    health_check,
)
from .http_client import service_client, ServiceClient
from .auth import (
    verify_internal_service_key,
    verify_jwt_token,
    verify_tenant_access,
)

__all__ = [
    # Shared library integrations
    "logger",
    "validateRequired",
    "successResponse",
    "errorResponse",
    "ValidationError",
    "DatabaseError",
    "ServiceError",
    "AuthenticationError",
    "init_database",
    "query",
    "health_check",
    # HTTP client
    "service_client",
    "ServiceClient",
    # Authentication
    "verify_internal_service_key",
    "verify_jwt_token",
    "verify_tenant_access",
]