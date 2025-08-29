"""Test metrics collection functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.as_infrastructure_service.services.metrics_collector import MetricsCollector
from src.as_infrastructure_service.services.redis_client import RedisClient
from src.as_infrastructure_service.services.health_checker import HealthChecker
from src.as_infrastructure_service.models.health import ServiceHealth, HealthCheckResult


class TestMetricsCollector:
    """Test metrics collection service."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        redis_client = Mock(spec=RedisClient)
        redis_client.store_service_metrics = AsyncMock(return_value=True)
        redis_client.store_system_metrics = AsyncMock(return_value=True)
        redis_client.get_active_alerts = AsyncMock(return_value=[])
        return redis_client
    
    @pytest.fixture
    def mock_health_checker(self):
        """Mock health checker."""
        health_checker = Mock(spec=HealthChecker)
        
        # Create sample service health data
        service_health = ServiceHealth(
            name="test-service",
            url="http://localhost:3000",
            port=3000,
            status='healthy',
            response_time=150,
            last_checked=datetime.utcnow(),
            uptime=99.5,
            critical=False
        )
        
        # Add some health history
        for i in range(10):
            service_health.health_history.append(
                HealthCheckResult(
                    timestamp=datetime.utcnow(),
                    status='healthy' if i < 8 else 'unhealthy',
                    response_time=100 + (i * 10),
                    http_status=200 if i < 8 else 500
                )
            )
        
        health_checker.service_states = {'test-service': service_health}
        health_checker.get_all_service_health = AsyncMock(return_value=[service_health])
        
        return health_checker
    
    @pytest.fixture
    def metrics_collector(self, mock_redis_client, mock_health_checker):
        """Create MetricsCollector instance."""
        return MetricsCollector(mock_redis_client, mock_health_checker)
    
    def test_calculate_percentile_empty_list(self, metrics_collector):
        """Test percentile calculation with empty list."""
        result = metrics_collector._calculate_percentile([], 95)
        assert result == 0.0
    
    def test_calculate_percentile_single_value(self, metrics_collector):
        """Test percentile calculation with single value."""
        result = metrics_collector._calculate_percentile([100], 95)
        assert result == 100
    
    def test_calculate_percentile_multiple_values(self, metrics_collector):
        """Test percentile calculation with multiple values."""
        values = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550]
        
        p50 = metrics_collector._calculate_percentile(values, 50)
        p95 = metrics_collector._calculate_percentile(values, 95)
        p99 = metrics_collector._calculate_percentile(values, 99)
        
        assert p50 == 300  # 50th percentile
        assert p95 == 525  # 95th percentile
        assert p99 == 550  # 99th percentile (max value for small list)
    
    def test_calculate_requests_per_minute_empty_history(self, metrics_collector):
        """Test requests per minute calculation with empty history."""
        result = metrics_collector._calculate_requests_per_minute([])
        assert result == 0.0
    
    def test_calculate_downtime_minutes_no_failures(self, metrics_collector):
        """Test downtime calculation with no failures."""
        history = [
            HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='healthy',
                response_time=100,
                http_status=200
            ) for _ in range(5)
        ]
        
        downtime = metrics_collector._calculate_downtime_minutes(history)
        assert downtime == 0.0
    
    def test_calculate_mtbf_empty_history(self, metrics_collector):
        """Test MTBF calculation with empty history."""
        result = metrics_collector._calculate_mtbf([])
        assert result == 0.0
    
    def test_calculate_mtbf_single_failure(self, metrics_collector):
        """Test MTBF calculation with single failure."""
        history = [
            HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='unhealthy',
                response_time=0,
                http_status=500
            )
        ]
        
        result = metrics_collector._calculate_mtbf(history)
        assert result == 0.0
    
    def test_calculate_mttr_no_failures(self, metrics_collector):
        """Test MTTR calculation with no failures."""
        history = [
            HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='healthy',
                response_time=100,
                http_status=200
            ) for _ in range(5)
        ]
        
        result = metrics_collector._calculate_mttr(history)
        assert result == 0.0
    
    @pytest.mark.asyncio
    async def test_collect_service_metrics_success(self, metrics_collector, mock_redis_client):
        """Test successful service metrics collection."""
        result = await metrics_collector.collect_service_metrics('test-service')
        
        assert result is not None
        assert result.service_name == 'test-service'
        assert isinstance(result.response_time, dict)
        assert isinstance(result.requests, dict)
        assert isinstance(result.availability, dict)
        
        # Should store metrics in Redis
        mock_redis_client.store_service_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_service_metrics_unknown_service(self, metrics_collector, mock_redis_client):
        """Test service metrics collection for unknown service."""
        result = await metrics_collector.collect_service_metrics('unknown-service')
        assert result is None
        
        # Should not store metrics
        mock_redis_client.store_service_metrics.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics_success(self, metrics_collector, mock_redis_client, mock_health_checker):
        """Test successful system metrics collection."""
        result = await metrics_collector.collect_system_metrics()
        
        assert result is not None
        assert result.total_services == 1
        assert result.healthy_services == 1  # Based on mock data
        assert result.degraded_services == 0
        assert result.unhealthy_services == 0
        assert result.alert_count == 0  # No active alerts in mock
        
        # Should store metrics in Redis
        mock_redis_client.store_system_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_collection(self, metrics_collector):
        """Test starting metrics collection."""
        await metrics_collector.start_collection(interval_seconds=1)
        
        # Should create collection task
        assert metrics_collector.collection_task is not None
        
        # Clean up
        await metrics_collector.stop_collection()
    
    @pytest.mark.asyncio
    async def test_stop_collection(self, metrics_collector):
        """Test stopping metrics collection."""
        # Start collection first
        await metrics_collector.start_collection(interval_seconds=1)
        
        # Stop collection
        await metrics_collector.stop_collection()
        
        # Task should be cancelled
        assert metrics_collector.collection_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_collect_all_metrics(self, metrics_collector, mock_redis_client):
        """Test collecting all metrics."""
        await metrics_collector.collect_all_metrics()
        
        # Should call both service and system metrics collection
        # Verify Redis store calls were made
        assert mock_redis_client.store_service_metrics.call_count >= 1
        assert mock_redis_client.store_system_metrics.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_service_metrics(self, metrics_collector, mock_redis_client):
        """Test retrieving service metrics."""
        mock_redis_client.get_service_metrics = AsyncMock(return_value={
            "response_time": {"current": 150},
            "requests": {"total": 100}
        })
        
        result = await metrics_collector.get_service_metrics('test-service')
        
        assert result is not None
        assert "response_time" in result
        assert "requests" in result
        
        mock_redis_client.get_service_metrics.assert_called_once_with('test-service')
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, metrics_collector, mock_redis_client):
        """Test retrieving system metrics."""
        mock_redis_client.get_system_metrics = AsyncMock(return_value={
            "total_services": 5,
            "healthy_services": 4
        })
        
        result = await metrics_collector.get_system_metrics()
        
        assert result is not None
        assert "total_services" in result
        
        mock_redis_client.get_system_metrics.assert_called_once()
    
    def test_calculate_system_requests_per_minute(self, metrics_collector, mock_health_checker):
        """Test system-wide requests per minute calculation."""
        services = [mock_health_checker.service_states['test-service']]
        
        result = metrics_collector._calculate_system_requests_per_minute(services)
        
        assert isinstance(result, int)
        assert result >= 0