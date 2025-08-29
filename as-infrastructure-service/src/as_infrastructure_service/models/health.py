"""Health monitoring data models."""

from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass


class HealthCheckResult(BaseModel):
    """Single health check result."""
    timestamp: datetime
    status: Literal['healthy', 'degraded', 'unhealthy']
    response_time: int  # milliseconds
    http_status: int
    
    # Optional fields
    error_message: Optional[str] = None
    service_version: Optional[str] = None
    database_connected: Optional[bool] = None
    external_services_ok: Optional[bool] = None


class ServiceHealth(BaseModel):
    """Complete health information for a service."""
    name: str
    url: str
    port: int
    health_endpoint: str = "/health"
    
    # Current status
    status: Literal['healthy', 'degraded', 'unhealthy', 'unknown']
    response_time: int  # milliseconds
    last_checked: datetime
    
    # Reliability metrics
    uptime: float = Field(default=0.0, description="Uptime percentage")
    consecutive_failures: int = Field(default=0)
    consecutive_successes: int = Field(default=0)
    
    # Historical data
    health_history: List[HealthCheckResult] = Field(default_factory=list)
    
    # Metadata
    environment: str = Field(default="production")
    dependencies: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    category: str = Field(default="core")
    critical: bool = Field(default=False)
    
    # Issues (for degraded status)
    issues: List[str] = Field(default_factory=list)


class ServiceMetrics(BaseModel):
    """Performance metrics for a service."""
    service_name: str
    timestamp: datetime
    
    # Response time metrics
    response_time: Dict[str, float] = Field(
        default_factory=lambda: {
            "current": 0,
            "average": 0,
            "p95": 0,
            "p99": 0
        }
    )
    
    # Request metrics
    requests: Dict[str, float] = Field(
        default_factory=lambda: {
            "total": 0,
            "perMinute": 0,
            "errorCount": 0,
            "errorRate": 0.0
        }
    )
    
    # Availability metrics
    availability: Dict[str, float] = Field(
        default_factory=lambda: {
            "uptime": 100.0,
            "downtimeMinutes": 0.0,
            "mtbf": 0.0,  # Mean Time Between Failures
            "mttr": 0.0   # Mean Time To Recovery
        }
    )


class SystemMetrics(BaseModel):
    """Overall system metrics."""
    timestamp: datetime
    
    # Service metrics
    total_services: int
    healthy_services: int
    degraded_services: int
    unhealthy_services: int
    
    # Performance metrics
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    
    # Request metrics
    total_requests: int
    requests_per_minute: int
    error_rate: float
    
    # System metrics
    system_uptime: float
    alert_count: int


class Alert(BaseModel):
    """Alert definition and state."""
    id: str
    type: Literal['service_down', 'high_response_time', 'high_error_rate', 'dependency_failure']
    severity: Literal['low', 'medium', 'high', 'critical']
    service: str
    
    # Alert details
    message: str
    description: str
    threshold: float
    current_value: float
    
    # Timing
    triggered_at: datetime
    
    # State
    status: Literal['active', 'acknowledged', 'resolved']
    
    # Optional fields
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class ServiceStatus(BaseModel):
    """Service status response model."""
    name: str
    status: Literal['healthy', 'degraded', 'unhealthy', 'unknown']
    url: str
    responseTime: int
    lastChecked: datetime
    uptime: float
    version: Optional[str] = None
    issues: List[str] = Field(default_factory=list)


class ServicesOverview(BaseModel):
    """Overview of all services."""
    services: List[ServiceStatus]
    summary: Dict[str, Any] = Field(
        default_factory=lambda: {
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "lastUpdated": datetime.utcnow().isoformat()
        }
    )


class SystemStatus(BaseModel):
    """Overall system status."""
    status: Literal['healthy', 'degraded', 'outage']
    timestamp: datetime
    version: str
    uptime: int  # seconds
    environment: str
    services: Dict[str, int] = Field(
        default_factory=lambda: {
            "total": 0,
            "healthy": 0,
            "unhealthy": 0,
            "unknown": 0
        }
    )


class CriticalStatus(BaseModel):
    """Critical system status for alerts."""
    critical: Dict[str, Any]
    alerts: List[Alert] = Field(default_factory=list)
    lastIncident: Optional[Dict[str, Any]] = None


class DashboardData(BaseModel):
    """Dashboard status data."""
    dashboard: Dict[str, Any]