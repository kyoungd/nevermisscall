"""Test health checking functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
import aiohttp

from src.as_infrastructure_service.services.health_checker import HealthChecker
from src.as_infrastructure_service.services.redis_client import RedisClient
from src.as_infrastructure_service.models.health import HealthCheckResult, ServiceHealth


class TestHealthChecker:
    """Test health checking service."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client."""
        redis_client = Mock(spec=RedisClient)
        redis_client.store_health_check = AsyncMock(return_value=True)
        redis_client.store_alert = AsyncMock(return_value=True)
        return redis_client
    
    @pytest.fixture
    def health_checker(self, mock_redis_client):
        """Create HealthChecker instance."""
        return HealthChecker(mock_redis_client)
    
    def test_extract_port_from_url(self, health_checker):
        """Test port extraction from URLs."""
        assert health_checker._extract_port("http://localhost:3000") == 3000
        assert health_checker._extract_port("https://localhost:8080/health") == 8080
        assert health_checker._extract_port("http://localhost") == 80
        assert health_checker._extract_port("https://localhost") == 443
    
    def test_determine_status_healthy(self, health_checker):
        """Test status determination for healthy service."""
        status = health_checker._determine_status(200, 150)
        assert status == 'healthy'
    
    def test_determine_status_degraded_slow_response(self, health_checker):
        """Test status determination for slow response."""
        status = health_checker._determine_status(200, 1500)  # 1.5 seconds
        assert status == 'degraded'
    
    def test_determine_status_degraded_client_error(self, health_checker):
        """Test status determination for client errors."""
        status = health_checker._determine_status(400, 100)
        assert status == 'degraded'
    
    def test_determine_status_unhealthy_server_error(self, health_checker):
        """Test status determination for server errors."""
        status = health_checker._determine_status(500, 100)
        assert status == 'unhealthy'
    
    def test_determine_status_unhealthy_very_slow(self, health_checker):
        """Test status determination for very slow response."""
        status = health_checker._determine_status(200, 4000)  # 4 seconds
        assert status == 'degraded'
    
    def test_get_service_dependencies(self, health_checker):
        """Test service dependency retrieval."""
        deps = health_checker._get_service_dependencies('as-call-service')
        
        # Should return list of dependencies
        assert isinstance(deps, list)
        
        # as-call-service should have dependencies
        expected_deps = ['ts-auth-service', 'ts-tenant-service', 'twilio-server', 'dispatch-bot-ai']
        for dep in expected_deps:
            assert dep in deps
    
    def test_get_service_dependencies_unknown_service(self, health_checker):
        """Test dependency retrieval for unknown service."""
        deps = health_checker._get_service_dependencies('unknown-service')
        assert deps == []
    
    def test_calculate_uptime_empty_history(self, health_checker):
        """Test uptime calculation with empty history."""
        uptime = health_checker._calculate_uptime([])
        assert uptime == 0.0
    
    def test_calculate_uptime_all_healthy(self, health_checker):
        """Test uptime calculation with all healthy checks."""
        history = [
            HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='healthy',
                response_time=100,
                http_status=200
            ) for _ in range(10)
        ]
        
        uptime = health_checker._calculate_uptime(history)
        assert uptime == 100.0
    
    def test_calculate_uptime_mixed_health(self, health_checker):
        """Test uptime calculation with mixed health status."""
        history = []
        
        # Add 8 healthy checks
        for _ in range(8):
            history.append(HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='healthy',
                response_time=100,
                http_status=200
            ))
        
        # Add 2 unhealthy checks
        for _ in range(2):
            history.append(HealthCheckResult(
                timestamp=datetime.utcnow(),
                status='unhealthy',
                response_time=0,
                http_status=500
            ))
        
        uptime = health_checker._calculate_uptime(history)
        assert uptime == 80.0  # 8/10 = 80%
    
    @pytest.mark.asyncio
    async def test_initialize(self, health_checker):
        """Test health checker initialization."""
        with patch('aiohttp.ClientSession') as mock_session:
            await health_checker.initialize()
            
            # Should create HTTP session
            mock_session.assert_called_once()
            
            # Should initialize service states
            assert len(health_checker.service_states) > 0
            
            # Check service state structure
            for service_name, service_state in health_checker.service_states.items():
                assert isinstance(service_state, ServiceHealth)
                assert service_state.name == service_name
                assert service_state.status == 'unknown'
    
    @pytest.mark.asyncio
    async def test_close(self, health_checker):
        """Test health checker cleanup."""
        # Mock session
        mock_session = Mock()
        mock_session.close = AsyncMock()
        health_checker.session = mock_session
        
        # Add mock monitoring task
        mock_task = Mock()
        mock_task.cancel = Mock()
        health_checker.monitoring_tasks['test-service'] = mock_task
        
        await health_checker.close()
        
        # Should cancel monitoring tasks
        mock_task.cancel.assert_called_once()
        
        # Should close session
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_service_state_healthy(self, health_checker, mock_redis_client):
        """Test service state update for healthy result."""
        # Initialize service states
        await health_checker.initialize()
        
        result = HealthCheckResult(
            timestamp=datetime.utcnow(),
            status='healthy',
            response_time=150,
            http_status=200
        )
        
        await health_checker._update_service_state('ts-auth-service', result)
        
        service = health_checker.service_states['ts-auth-service']
        assert service.status == 'healthy'
        assert service.response_time == 150
        assert service.consecutive_successes == 1
        assert service.consecutive_failures == 0
        assert len(service.health_history) == 1
        assert len(service.issues) == 0
    
    @pytest.mark.asyncio
    async def test_update_service_state_unhealthy(self, health_checker, mock_redis_client):
        """Test service state update for unhealthy result."""
        # Initialize service states
        await health_checker.initialize()
        
        result = HealthCheckResult(
            timestamp=datetime.utcnow(),
            status='unhealthy',
            response_time=0,
            http_status=500,
            error_message="Connection refused"
        )
        
        await health_checker._update_service_state('ts-auth-service', result)
        
        service = health_checker.service_states['ts-auth-service']
        assert service.status == 'unhealthy'
        assert service.consecutive_failures == 1
        assert service.consecutive_successes == 0
        assert len(service.issues) > 0
        assert "Connection refused" in service.issues
    
    @pytest.mark.asyncio
    async def test_update_service_state_degraded(self, health_checker, mock_redis_client):
        """Test service state update for degraded result."""
        # Initialize service states
        await health_checker.initialize()
        
        result = HealthCheckResult(
            timestamp=datetime.utcnow(),
            status='degraded',
            response_time=1500,  # Slow response
            http_status=200
        )
        
        await health_checker._update_service_state('ts-auth-service', result)
        
        service = health_checker.service_states['ts-auth-service']
        assert service.status == 'degraded'
        assert len(service.issues) > 0
        assert any("High response time" in issue for issue in service.issues)
    
    @pytest.mark.asyncio
    async def test_handle_health_check_failure(self, health_checker, mock_redis_client):
        """Test handling of health check failures."""
        # Initialize service states
        await health_checker.initialize()
        
        result = await health_checker._handle_health_check_failure(
            'ts-auth-service',
            'timeout',
            'Request timeout after 5 seconds'
        )
        
        assert result.status == 'unhealthy'
        assert result.response_time == 0
        assert result.http_status == 0
        assert "timeout" in result.error_message
        
        # Should update service state
        service = health_checker.service_states['ts-auth-service']
        assert service.status == 'unhealthy'
        assert service.consecutive_failures == 1
    
    @pytest.mark.asyncio
    async def test_get_all_service_health(self, health_checker):
        """Test retrieving all service health states."""
        # Initialize service states
        await health_checker.initialize()
        
        all_health = await health_checker.get_all_service_health()
        
        assert isinstance(all_health, list)
        assert len(all_health) > 0
        
        for health in all_health:
            assert isinstance(health, ServiceHealth)
    
    @pytest.mark.asyncio
    async def test_get_service_health_existing(self, health_checker):
        """Test retrieving health for existing service."""
        # Initialize service states
        await health_checker.initialize()
        
        health = await health_checker.get_service_health('ts-auth-service')
        
        assert health is not None
        assert isinstance(health, ServiceHealth)
        assert health.name == 'ts-auth-service'
    
    @pytest.mark.asyncio
    async def test_get_service_health_nonexistent(self, health_checker):
        """Test retrieving health for non-existent service."""
        # Initialize service states
        await health_checker.initialize()
        
        health = await health_checker.get_service_health('nonexistent-service')
        assert health is None