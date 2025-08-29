"""API response models."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """Standard API response format."""
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    uptime: int
    environment: str
    services: Dict[str, int]


class ServiceDiscoveryResponse(BaseModel):
    """Service discovery response."""
    services: Dict[str, Dict[str, Any]]
    lastUpdated: datetime


class DependencyResponse(BaseModel):
    """Service dependency response."""
    dependencies: Dict[str, Any]
    criticalPath: list
    healthyDependencies: int
    brokenDependencies: int


def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create a successful API response."""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def error_response(message: str, error: Optional[str] = None) -> Dict[str, Any]:
    """Create an error API response."""
    response = {
        "success": False,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    if error:
        response["error"] = error
    return response