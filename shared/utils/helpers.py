"""
Helper functions for NeverMissCall shared library.

Provides date helpers, string utilities, ID generation, and FastAPI
middleware helpers following the patterns defined in shared.md.
"""

import uuid
import re
import html
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from ..models.exceptions import UnauthorizedError
from .logger import logger


def format_date(date: datetime | str) -> str:
    """
    Format date to ISO string format.
    
    Args:
        date: datetime object or ISO string
        
    Returns:
        ISO formatted date string
    """
    if isinstance(date, str):
        try:
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        except ValueError:
            return date  # Return as-is if parsing fails
    
    if isinstance(date, datetime):
        # Ensure UTC timezone
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.isoformat()
    
    return str(date)


def is_valid_date(date_string: str) -> bool:
    """
    Check if date string is valid ISO format.
    
    Args:
        date_string: Date string to validate
        
    Returns:
        True if valid date format, False otherwise
    """
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_string(string: str) -> str:
    """
    Sanitize string by removing/escaping dangerous characters.
    
    Args:
        string: String to sanitize
        
    Returns:
        Sanitized string
    """
    if not isinstance(string, str):
        return str(string)
    
    # HTML escape
    sanitized = html.escape(string)
    
    # Remove control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def generate_id() -> str:
    """
    Generate a new UUID string.
    
    Returns:
        UUID string in standard format
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    Generate a shorter ID for display purposes.
    
    Args:
        length: Length of the short ID
        
    Returns:
        Short ID string (alphanumeric)
    """
    import random
    import string
    
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def normalize_phone_number(phone: str) -> str:
    """
    Normalize phone number to E.164 format.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        Phone number in E.164 format (+1XXXXXXXXXX)
    """
    if not phone:
        return phone
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Handle US numbers
    if len(digits_only) == 10:
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+{digits_only}"
    
    # If already in E.164 format or international
    if phone.startswith('+'):
        return phone
    
    # Default to US format for 10-digit numbers
    return f"+1{digits_only}" if len(digits_only) == 10 else phone


def format_phone_display(phone: str) -> str:
    """
    Format phone number for display.
    
    Args:
        phone: Phone number in E.164 format
        
    Returns:
        Formatted phone number for display (e.g., (555) 123-4567)
    """
    if not phone:
        return phone
    
    # Extract digits
    digits = re.sub(r'\D', '', phone)
    
    # US numbers
    if len(digits) == 11 and digits.startswith('1'):
        area_code = digits[1:4]
        exchange = digits[4:7]
        number = digits[7:11]
        return f"({area_code}) {exchange}-{number}"
    elif len(digits) == 10:
        area_code = digits[0:3]
        exchange = digits[3:6]
        number = digits[6:10]
        return f"({area_code}) {exchange}-{number}"
    
    # Return as-is for international numbers
    return phone


def truncate_string(string: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        string: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if not string or len(string) <= max_length:
        return string
    
    return string[:max_length - len(suffix)] + suffix


def async_handler(func: Callable) -> Callable:
    """
    Async handler decorator for FastAPI routes.
    
    Provides consistent error handling and logging for async route handlers.
    
    Args:
        func: Async function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as error:
            logger.error(f"Async handler error in {func.__name__}", error=error)
            raise
    
    return wrapper


def require_service_auth(service_key: str):
    """
    FastAPI dependency for service-to-service authentication.
    
    Validates the X-Service-Key header for internal service calls
    following the authentication patterns in authentication-standards.md.
    
    Args:
        service_key: Expected service authentication key
        
    Returns:
        FastAPI dependency function
    """
    def authenticate_service(request: Request) -> bool:
        """
        Authenticate service request using X-Service-Key header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if authenticated
            
        Raises:
            HTTPException: If authentication fails
        """
        auth_header = request.headers.get('X-Service-Key')
        
        if not auth_header:
            logger.warn("Missing X-Service-Key header", extra={
                'path': request.url.path,
                'method': request.method
            })
            raise HTTPException(status_code=401, detail="Missing service authentication key")
        
        if auth_header != service_key:
            logger.warn("Invalid X-Service-Key header", extra={
                'path': request.url.path,
                'method': request.method,
                'provided_key': auth_header[:8] + "..." if len(auth_header) > 8 else auth_header
            })
            raise HTTPException(status_code=401, detail="Invalid service authentication key")
        
        logger.debug("Service authentication successful", extra={
            'path': request.url.path,
            'method': request.method
        })
        
        return True
    
    return Depends(authenticate_service)


def require_jwt_auth():
    """
    FastAPI dependency for JWT authentication.
    
    Validates the Authorization Bearer token for user-facing endpoints
    following the authentication patterns in authentication-standards.md.
    
    Returns:
        FastAPI dependency function
    """
    security = HTTPBearer()
    
    def authenticate_jwt(request: Request, token: str = Depends(security)) -> Dict[str, Any]:
        """
        Authenticate JWT token from Authorization header.
        
        Args:
            request: FastAPI request object
            token: JWT token from Authorization header
            
        Returns:
            Decoded JWT payload
            
        Raises:
            HTTPException: If authentication fails
        """
        try:
            import jwt
            import os
            
            jwt_secret = os.getenv('JWT_SECRET', 'e8a3b5c7d9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6')
            
            # Decode and verify JWT token
            payload = jwt.decode(token.credentials, jwt_secret, algorithms=['HS256'])
            
            logger.debug("JWT authentication successful", extra={
                'path': request.url.path,
                'method': request.method,
                'user_id': payload.get('user_id'),
                'tenant_id': payload.get('tenant_id')
            })
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warn("Expired JWT token", extra={
                'path': request.url.path,
                'method': request.method
            })
            raise HTTPException(status_code=401, detail="Token has expired")
        
        except jwt.InvalidTokenError as error:
            logger.warn("Invalid JWT token", extra={
                'path': request.url.path,
                'method': request.method,
                'error': str(error)
            })
            raise HTTPException(status_code=401, detail="Invalid token")
        
        except Exception as error:
            logger.error("JWT authentication error", error=error, extra={
                'path': request.url.path,
                'method': request.method
            })
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    return Depends(authenticate_jwt)


def extract_tenant_id(request: Request, jwt_payload: Optional[Dict[str, Any]] = None) -> str:
    """
    Extract tenant ID from request headers or JWT payload.
    
    Args:
        request: FastAPI request object
        jwt_payload: Optional JWT payload from authentication
        
    Returns:
        Tenant ID string
        
    Raises:
        HTTPException: If tenant ID not found
    """
    # Try to get from JWT payload first
    if jwt_payload and 'tenant_id' in jwt_payload:
        return jwt_payload['tenant_id']
    
    # Try to get from X-Tenant-ID header
    tenant_id = request.headers.get('X-Tenant-ID')
    if tenant_id:
        return tenant_id
    
    # Try to get from query parameters
    tenant_id = request.query_params.get('tenant_id')
    if tenant_id:
        return tenant_id
    
    raise HTTPException(status_code=400, detail="Tenant ID required")


def create_correlation_id() -> str:
    """
    Create correlation ID for request tracking.
    
    Returns:
        Correlation ID string
    """
    return generate_short_id(12)


def parse_sort_params(sort: Optional[str] = None) -> Dict[str, str]:
    """
    Parse sort parameters from query string.
    
    Args:
        sort: Sort parameter string (e.g., "created_at:desc,name:asc")
        
    Returns:
        Dictionary of field -> direction mappings
    """
    if not sort:
        return {'created_at': 'desc'}  # Default sort
    
    sort_params = {}
    
    for sort_item in sort.split(','):
        if ':' in sort_item:
            field, direction = sort_item.strip().split(':', 1)
            direction = direction.lower()
            
            if direction in ['asc', 'desc']:
                sort_params[field.strip()] = direction
    
    return sort_params if sort_params else {'created_at': 'desc'}


def calculate_pagination_info(page: int, limit: int, total: int) -> Dict[str, Any]:
    """
    Calculate pagination information.
    
    Args:
        page: Current page (1-based)
        limit: Items per page
        total: Total number of items
        
    Returns:
        Dictionary with pagination info
    """
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return {
        'page': page,
        'limit': limit,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_previous': page > 1,
        'offset': (page - 1) * limit
    }