"""
API response models and helpers for NeverMissCall shared library.

Provides standardized API response patterns following the 
api-integration-patterns.md documentation.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """
    Standard API response model for all NeverMissCall services.
    
    Follows the response format defined in api-integration-patterns.md
    for consistent service communication.
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthStatus(BaseModel):
    """
    Health status model for service monitoring.
    
    Used by infrastructure-service for health checks and
    monitoring across all microservices.
    """
    status: Literal['healthy', 'unhealthy', 'degraded']
    service: str
    version: Optional[str] = None
    uptime: Optional[int] = None  # seconds
    dependencies: Optional[Dict[str, Literal['healthy', 'unhealthy']]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Additional health check details
    database_status: Optional[Literal['healthy', 'unhealthy']] = None
    memory_usage: Optional[float] = None  # percentage
    cpu_usage: Optional[float] = None  # percentage
    error_count: Optional[int] = None
    last_error: Optional[str] = None


class ErrorDetails(BaseModel):
    """
    Detailed error information for API responses.
    
    Follows the error handling patterns defined in
    api-integration-patterns.md.
    """
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    field: Optional[str] = None  # For validation errors
    correlation_id: Optional[str] = None


class PaginatedResponse(BaseModel):
    """
    Paginated response model for list endpoints.
    
    Used by repository pattern for consistent pagination
    across all services.
    """
    data: list
    total: int
    page: int
    limit: int
    has_next: bool = False
    has_previous: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate pagination flags
        total_pages = (self.total + self.limit - 1) // self.limit
        self.has_next = self.page < total_pages
        self.has_previous = self.page > 1


def success_response(data: Any = None, message: Optional[str] = None) -> ApiResponse:
    """
    Create successful API response.
    
    Args:
        data: Response data (optional)
        message: Success message (optional)
        
    Returns:
        ApiResponse with success=True
    """
    return ApiResponse(
        success=True,
        data=data,
        message=message
    )


def error_response(error: str, data: Optional[Any] = None, details: Optional[Dict[str, Any]] = None) -> ApiResponse:
    """
    Create error API response.
    
    Args:
        error: Error message
        data: Optional error data
        details: Optional error details dictionary
        
    Returns:
        ApiResponse with success=False
    """
    response_data = data
    
    # If details provided, wrap in ErrorDetails
    if details:
        error_details = ErrorDetails(
            code=details.get('code', 'UNKNOWN_ERROR'),
            message=error,
            details=details.get('details'),
            field=details.get('field'),
            correlation_id=details.get('correlation_id')
        )
        response_data = error_details.dict()
    
    return ApiResponse(
        success=False,
        error=error,
        data=response_data
    )


def validation_error_response(field: str, message: str, value: Any = None) -> ApiResponse:
    """
    Create validation error response.
    
    Args:
        field: Field name that failed validation
        message: Validation error message
        value: Invalid value (optional)
        
    Returns:
        ApiResponse for validation error
    """
    details = {
        'code': 'VALIDATION_ERROR',
        'field': field,
        'details': {'invalid_value': value} if value is not None else None
    }
    
    return error_response(message, details=details)


def not_found_response(resource: str, identifier: str = None) -> ApiResponse:
    """
    Create not found error response.
    
    Args:
        resource: Resource type (e.g., 'user', 'conversation')
        identifier: Resource identifier (optional)
        
    Returns:
        ApiResponse for not found error
    """
    message = f"{resource.title()} not found"
    if identifier:
        message += f": {identifier}"
    
    details = {
        'code': 'NOT_FOUND',
        'details': {
            'resource': resource,
            'identifier': identifier
        }
    }
    
    return error_response(message, details=details)


def unauthorized_response(reason: str = "Authentication required") -> ApiResponse:
    """
    Create unauthorized error response.
    
    Args:
        reason: Reason for unauthorized access
        
    Returns:
        ApiResponse for unauthorized error
    """
    details = {
        'code': 'UNAUTHORIZED',
        'details': {'reason': reason}
    }
    
    return error_response("Unauthorized access", details=details)


def service_unavailable_response(service: str, reason: str = "Service temporarily unavailable") -> ApiResponse:
    """
    Create service unavailable error response.
    
    Args:
        service: Service name
        reason: Reason for unavailability
        
    Returns:
        ApiResponse for service unavailable error
    """
    details = {
        'code': 'SERVICE_UNAVAILABLE',
        'details': {
            'service': service,
            'reason': reason
        }
    }
    
    return error_response(f"{service} is unavailable", details=details)