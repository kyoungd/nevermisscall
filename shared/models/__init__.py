"""
Models module for NeverMissCall shared library.

Provides Pydantic models and response helpers following the patterns
defined in shared.md documentation and database schema.
"""

from .api import (
    ApiResponse,
    success_response,
    error_response,
    HealthStatus
)

from .auth import (
    User,
    Tenant,
    JwtPayload
)

from .core import (
    Call,
    Conversation,
    Message,
    Lead,
    PhoneNumber
)

from .exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError
)

__all__ = [
    # API Response models
    "ApiResponse",
    "success_response", 
    "error_response",
    "HealthStatus",
    
    # Authentication models
    "User",
    "Tenant", 
    "JwtPayload",
    
    # Core business models
    "Call",
    "Conversation",
    "Message", 
    "Lead",
    "PhoneNumber",
    
    # Exception classes
    "ValidationError",
    "NotFoundError", 
    "UnauthorizedError"
]