"""API response models."""

from datetime import datetime
from typing import Any, Optional, Dict, Union
from pydantic import BaseModel, Field
from enum import Enum

from .user import UserResponse, TokenPair


class ErrorCode(str, Enum):
    """Standard error codes."""
    
    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    
    # Token errors
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    REFRESH_TOKEN_INVALID = "REFRESH_TOKEN_INVALID"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    WEAK_PASSWORD = "WEAK_PASSWORD"
    INVALID_EMAIL = "INVALID_EMAIL"
    
    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Generic errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    FORBIDDEN = "FORBIDDEN"


class ErrorDetail(BaseModel):
    """Error detail information."""
    
    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ApiResponse(BaseModel):
    """Base API response model."""
    
    success: bool = Field(..., description="Success status")
    message: Optional[str] = Field(None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class SuccessResponse(ApiResponse):
    """Success response model."""
    
    success: bool = Field(default=True)
    data: Optional[Any] = Field(None, description="Response data")


class ErrorResponse(ApiResponse):
    """Error response model."""
    
    success: bool = Field(default=False)
    error: ErrorDetail = Field(..., description="Error information")


class AuthSuccessResponse(SuccessResponse):
    """Authentication success response."""
    
    user: UserResponse = Field(..., description="User information")
    tokens: TokenPair = Field(..., description="Authentication tokens")


class LoginResponse(AuthSuccessResponse):
    """Login response model."""
    pass


class RegisterResponse(AuthSuccessResponse):
    """Registration response model."""
    pass


class RefreshResponse(SuccessResponse):
    """Token refresh response model."""
    
    tokens: TokenPair = Field(..., description="New authentication tokens")


class LogoutResponse(SuccessResponse):
    """Logout response model."""
    
    message: str = Field(default="Logged out successfully")


class TokenValidationResponse(BaseModel):
    """Token validation response model."""
    
    valid: bool = Field(..., description="Token validity status")
    user: Optional[UserResponse] = Field(None, description="User information if token is valid")
    error: Optional[str] = Field(None, description="Error message if token is invalid")


class UserProfileResponse(SuccessResponse):
    """User profile response model."""
    
    user: UserResponse = Field(..., description="User profile information")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: str = Field(..., description="Database connection status")
    uptime: Optional[str] = Field(None, description="Service uptime")


# Response helper functions
def success_response(
    data: Any = None, 
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Create a success response."""
    response = {
        "success": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if message:
        response["message"] = message
    
    if data is not None:
        response["data"] = data
    
    return response


def error_response(
    code: Union[ErrorCode, str],
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error response."""
    if isinstance(code, str):
        code = ErrorCode(code) if code in ErrorCode.__members__.values() else ErrorCode.INTERNAL_SERVER_ERROR
    
    return {
        "success": False,
        "error": {
            "code": code.value,
            "message": message,
            "details": details or {}
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def auth_success_response(
    user: UserResponse, 
    tokens: TokenPair, 
    message: str = "Authentication successful"
) -> Dict[str, Any]:
    """Create an authentication success response."""
    return {
        "success": True,
        "message": message,
        "user": user.dict(),
        "tokens": tokens.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }


def validation_error_response(errors: list) -> Dict[str, Any]:
    """Create a validation error response."""
    return error_response(
        ErrorCode.VALIDATION_ERROR,
        "Validation failed",
        {"validation_errors": errors}
    )