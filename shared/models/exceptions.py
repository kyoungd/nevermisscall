"""
Exception classes for NeverMissCall shared library.

Provides custom exception classes following the error handling
patterns defined in api-integration-patterns.md.
"""

from typing import Optional, Dict, Any


class ValidationError(Exception):
    """
    Validation error for input validation failures.
    
    Raised when request data fails validation or business rule checks.
    """
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation (optional)
            details: Additional error details (optional)
        """
        super().__init__(message)
        self.field = field
        self.details = details or {}
        self.code = 'VALIDATION_ERROR'


class NotFoundError(Exception):
    """
    Resource not found error.
    
    Raised when a requested resource (user, conversation, etc.) is not found.
    """
    
    def __init__(self, message: Optional[str] = None, resource: Optional[str] = None, identifier: Optional[str] = None):
        """
        Initialize not found error.
        
        Args:
            message: Error message (optional, will be generated if not provided)
            resource: Resource type (e.g., 'user', 'conversation')
            identifier: Resource identifier
        """
        if not message:
            if resource:
                message = f"{resource.title()} not found"
                if identifier:
                    message += f": {identifier}"
            else:
                message = "Resource not found"
        
        super().__init__(message)
        self.resource = resource
        self.identifier = identifier
        self.code = 'NOT_FOUND'


class UnauthorizedError(Exception):
    """
    Unauthorized access error.
    
    Raised when authentication fails or access is denied.
    """
    
    def __init__(self, message: Optional[str] = None, reason: Optional[str] = None):
        """
        Initialize unauthorized error.
        
        Args:
            message: Error message (optional)
            reason: Reason for unauthorized access (optional)
        """
        if not message:
            message = "Unauthorized access" + (f": {reason}" if reason else "")
        
        super().__init__(message)
        self.reason = reason
        self.code = 'UNAUTHORIZED'


class ForbiddenError(Exception):
    """
    Forbidden access error.
    
    Raised when user is authenticated but lacks permissions for the resource.
    """
    
    def __init__(self, message: Optional[str] = None, resource: Optional[str] = None):
        """
        Initialize forbidden error.
        
        Args:
            message: Error message (optional)
            resource: Resource being accessed (optional)
        """
        if not message:
            message = "Access forbidden"
            if resource:
                message += f" for {resource}"
        
        super().__init__(message)
        self.resource = resource
        self.code = 'FORBIDDEN'


class ConflictError(Exception):
    """
    Resource conflict error.
    
    Raised when a resource already exists or conflicts with current state.
    """
    
    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize conflict error.
        
        Args:
            message: Error message
            resource: Resource type (optional)
            details: Additional conflict details (optional)
        """
        super().__init__(message)
        self.resource = resource
        self.details = details or {}
        self.code = 'CONFLICT'


class BusinessRuleError(Exception):
    """
    Business rule violation error.
    
    Raised when an operation violates business logic or rules.
    """
    
    def __init__(self, message: str, rule: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """
        Initialize business rule error.
        
        Args:
            message: Error message
            rule: Business rule that was violated (optional)
            context: Additional context about the violation (optional)
        """
        super().__init__(message)
        self.rule = rule
        self.context = context or {}
        self.code = 'BUSINESS_RULE_VIOLATION'


class ExternalServiceError(Exception):
    """
    External service error.
    
    Raised when external service (Twilio, OpenAI, etc.) fails or is unavailable.
    """
    
    def __init__(self, message: str, service: str, status_code: Optional[int] = None, response: Optional[str] = None):
        """
        Initialize external service error.
        
        Args:
            message: Error message
            service: Service name (e.g., 'twilio', 'openai')
            status_code: HTTP status code (optional)
            response: Service response (optional)
        """
        super().__init__(message)
        self.service = service
        self.status_code = status_code
        self.response = response
        self.code = 'EXTERNAL_SERVICE_ERROR'


class DatabaseError(Exception):
    """
    Database operation error.
    
    Raised when database operations fail.
    """
    
    def __init__(self, message: str, operation: Optional[str] = None, table: Optional[str] = None):
        """
        Initialize database error.
        
        Args:
            message: Error message
            operation: Database operation (select, insert, update, delete)
            table: Table name (optional)
        """
        super().__init__(message)
        self.operation = operation
        self.table = table
        self.code = 'DATABASE_ERROR'


class RateLimitError(Exception):
    """
    Rate limit exceeded error.
    
    Raised when API rate limits are exceeded.
    """
    
    def __init__(self, message: str, limit: Optional[int] = None, reset_time: Optional[int] = None):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            limit: Rate limit value (optional)
            reset_time: Time when rate limit resets (optional)
        """
        super().__init__(message)
        self.limit = limit
        self.reset_time = reset_time
        self.code = 'RATE_LIMIT_EXCEEDED'


class ConfigurationError(Exception):
    """
    Configuration error.
    
    Raised when service configuration is invalid or missing.
    """
    
    def __init__(self, message: str, setting: Optional[str] = None):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            setting: Configuration setting name (optional)
        """
        super().__init__(message)
        self.setting = setting
        self.code = 'CONFIGURATION_ERROR'