"""
Utilities module for NeverMissCall shared library.

Provides logging, HTTP client, validation functions, and helper utilities
following the patterns defined in shared.md documentation.
"""

from .logger import logger
from .client import ServiceClient
from .validation import (
    validate_required,
    validate_email,
    validate_phone_number,
    validate_uuid,
    validate_password
)
from .helpers import (
    format_date,
    is_valid_date,
    sanitize_string,
    generate_id,
    async_handler,
    require_service_auth
)

__all__ = [
    # Logger
    "logger",
    
    # HTTP Client
    "ServiceClient",
    
    # Validation functions
    "validate_required",
    "validate_email",
    "validate_phone_number", 
    "validate_uuid",
    "validate_password",
    
    # Helper functions
    "format_date",
    "is_valid_date",
    "sanitize_string",
    "generate_id",
    "async_handler",
    "require_service_auth"
]