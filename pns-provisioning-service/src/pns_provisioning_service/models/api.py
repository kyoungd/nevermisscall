"""API response models."""

from datetime import datetime
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """Standard API response format."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response format."""
    success: bool = Field(default=False)
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorDetail(BaseModel):
    """Error detail information."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create a successful API response."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create an error API response."""
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# Common error codes
class ErrorCodes:
    TENANT_ALREADY_HAS_NUMBER = "TENANT_ALREADY_HAS_NUMBER"
    NUMBER_PROVISIONING_FAILED = "NUMBER_PROVISIONING_FAILED"
    INVALID_AREA_CODE = "INVALID_AREA_CODE"
    WEBHOOK_CONFIGURATION_FAILED = "WEBHOOK_CONFIGURATION_FAILED"
    MESSAGING_SERVICE_CREATION_FAILED = "MESSAGING_SERVICE_CREATION_FAILED"
    TWILIO_API_ERROR = "TWILIO_API_ERROR"
    PHONE_NUMBER_NOT_FOUND = "PHONE_NUMBER_NOT_FOUND"
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"