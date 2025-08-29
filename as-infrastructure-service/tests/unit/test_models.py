"""Test health monitoring models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.as_infrastructure_service.models.health import (
    HealthCheckResult,
    ServiceHealth,
    ServiceMetrics,
    SystemMetrics,
    Alert
)


class TestHealthModels:
    """Test health monitoring data models."""
    
    def test_health_check_result_creation(self):
        """Test HealthCheckResult model creation."""
        result = HealthCheckResult(
            timestamp=datetime.utcnow(),
            status='healthy',
            response_time=150,
            http_status=200
        )
        
        assert result.status == 'healthy'
        assert result.response_time == 150
        assert result.http_status == 200
        assert result.error_message is None
    
    def test_health_check_result_with_error(self):
        """Test HealthCheckResult with error information."""
        result = HealthCheckResult(
            timestamp=datetime.utcnow(),
            status='unhealthy',
            response_time=0,
            http_status=500,
            error_message="Connection timeout"
        )
        
        assert result.status == 'unhealthy'
        assert result.error_message == "Connection timeout"
    
    def test_health_check_result_invalid_status(self):
        """Test HealthCheckResult with invalid status."""
        with pytest.raises(ValidationError):
            HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='invalid_status',  # Invalid status
                response_time=150,
                http_status=200
            )
    
    def test_service_health_creation(self):
        """Test ServiceHealth model creation."""
        service = ServiceHealth(
            name="test-service",
            url="http://localhost:3000",
            port=3000,
            status='healthy',
            response_time=120,
            last_checked=datetime.utcnow()
        )
        
        assert service.name == "test-service"
        assert service.status == 'healthy'
        assert service.uptime == 0.0  # Default value
        assert service.consecutive_failures == 0
        assert len(service.health_history) == 0
    
    def test_service_health_with_history(self):
        """Test ServiceHealth with health history."""
        history = [
            HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='healthy',
                response_time=100,
                http_status=200
            )
        ]
        
        service = ServiceHealth(
            name="test-service",
            url="http://localhost:3000",
            port=3000,
            status='healthy',
            response_time=120,
            last_checked=datetime.utcnow(),
            health_history=history
        )
        
        assert len(service.health_history) == 1
        assert service.health_history[0].status == 'healthy'
    
    def test_service_metrics_creation(self):
        """Test ServiceMetrics model creation."""
        metrics = ServiceMetrics(
            service_name="test-service",
            timestamp=datetime.utcnow()
        )
        
        assert metrics.service_name == "test-service"
        assert "current" in metrics.response_time
        assert "total" in metrics.requests
        assert "uptime" in metrics.availability
    
    def test_system_metrics_creation(self):
        """Test SystemMetrics model creation."""
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            total_services=5,
            healthy_services=4,
            degraded_services=1,
            unhealthy_services=0,
            average_response_time=150.5,
            p95_response_time=200.0,
            p99_response_time=250.0,
            total_requests=1000,
            requests_per_minute=60,
            error_rate=0.01,
            system_uptime=99.5,
            alert_count=1
        )
        
        assert metrics.total_services == 5
        assert metrics.healthy_services == 4
        assert metrics.error_rate == 0.01
    
    def test_alert_creation(self):
        """Test Alert model creation."""
        alert = Alert(
            id="alert-123",
            type='high_response_time',
            severity='critical',
            service="test-service",
            message="Response time too high",
            description="Service response time exceeded 3 seconds",
            threshold=3000.0,
            current_value=3500.0,
            triggered_at=datetime.utcnow(),
            status='active'
        )
        
        assert alert.type == 'high_response_time'
        assert alert.severity == 'critical'
        assert alert.current_value > alert.threshold
        assert alert.status == 'active'
    
    def test_alert_invalid_type(self):
        """Test Alert with invalid type."""
        with pytest.raises(ValidationError):
            Alert(
                id="alert-123",
                type='invalid_type',  # Invalid type
                severity='critical',
                service="test-service",
                message="Test alert",
                description="Test description",
                threshold=100.0,
                current_value=150.0,
                triggered_at=datetime.utcnow(),
                status='active'
            )