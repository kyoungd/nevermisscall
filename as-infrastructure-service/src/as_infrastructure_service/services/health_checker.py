"""Health checking service for monitoring all services."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Literal
import aiohttp

from ..config.settings import SERVICE_REGISTRY, ALERT_THRESHOLDS, settings
from ..models.health import HealthCheckResult, ServiceHealth, Alert
from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """Monitors health of all registered services."""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.session: Optional[aiohttp.ClientSession] = None
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.service_states: Dict[str, ServiceHealth] = {}
    
    async def initialize(self):
        """Initialize health checker."""
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(
            total=settings.health_check_timeout_ms / 1000
        )
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Initialize service states
        for service_name, config in SERVICE_REGISTRY.items():
            self.service_states[service_name] = ServiceHealth(
                name=service_name,
                url=config['url'],
                port=self._extract_port(config['url']),
                health_endpoint=config['health_endpoint'],
                status='unknown',
                response_time=0,
                last_checked=datetime.utcnow(),
                category=config.get('category', 'core'),
                critical=config.get('critical', False),
                dependencies=self._get_service_dependencies(service_name)
            )
        
        logger.info("Health checker initialized")
    
    async def close(self):
        """Close health checker."""
        # Cancel monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        
        # Close HTTP session
        if self.session:
            await self.session.close()
        
        logger.info("Health checker closed")
    
    def _extract_port(self, url: str) -> int:
        """Extract port from URL."""
        try:
            if ':' in url.split('//')[-1]:
                return int(url.split(':')[-1].split('/')[0])
            return 80 if url.startswith('http://') else 443
        except:
            return 0
    
    def _get_service_dependencies(self, service_name: str) -> List[str]:
        """Get service dependencies."""
        from ..config.settings import SERVICE_DEPENDENCIES
        return SERVICE_DEPENDENCIES.get(service_name, [])
    
    async def start_monitoring(self):
        """Start monitoring all services."""
        for service_name, config in SERVICE_REGISTRY.items():
            check_interval = config['check_interval'] / 1000  # Convert to seconds
            task = asyncio.create_task(
                self._monitor_service(service_name, check_interval)
            )
            self.monitoring_tasks[service_name] = task
        
        logger.info(f"Started monitoring {len(SERVICE_REGISTRY)} services")
    
    async def _monitor_service(self, service_name: str, interval: float):
        """Monitor a single service continuously."""
        while True:
            try:
                await self.check_service_health(service_name)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for {service_name}")
                break
            except Exception as e:
                logger.error(f"Error monitoring {service_name}: {e}")
                await asyncio.sleep(interval)
    
    async def check_service_health(self, service_name: str) -> Optional[HealthCheckResult]:
        """Check health of a single service."""
        config = SERVICE_REGISTRY.get(service_name)
        if not config:
            return None
        
        start_time = datetime.utcnow()
        
        try:
            url = f"{config['url']}{config['health_endpoint']}"
            timeout = aiohttp.ClientTimeout(total=config['timeout'] / 1000)
            
            async with self.session.get(url, timeout=timeout) as response:
                end_time = datetime.utcnow()
                response_time = int((end_time - start_time).total_seconds() * 1000)
                
                # Determine status based on response
                status = self._determine_status(response.status, response_time)
                
                # Parse response for additional info
                service_version = None
                database_connected = None
                
                try:
                    data = await response.json()
                    service_version = data.get('version')
                    database_connected = data.get('database', {}).get('connected')
                except:
                    pass
                
                result = HealthCheckResult(
                    timestamp=end_time,
                    status=status,
                    response_time=response_time,
                    http_status=response.status,
                    service_version=service_version,
                    database_connected=database_connected
                )
                
                # Update service state
                await self._update_service_state(service_name, result)
                
                # Store result in Redis
                await self.redis_client.store_health_check(service_name, {
                    "status": status,
                    "response_time": response_time,
                    "timestamp": end_time.isoformat(),
                    "http_status": response.status,
                    "consecutive_failures": self.service_states[service_name].consecutive_failures,
                    "consecutive_successes": self.service_states[service_name].consecutive_successes
                })
                
                logger.debug(f"Health check {service_name}: {status} ({response_time}ms)")
                return result
                
        except asyncio.TimeoutError:
            return await self._handle_health_check_failure(
                service_name, "timeout", "Request timeout"
            )
        except aiohttp.ClientError as e:
            return await self._handle_health_check_failure(
                service_name, "connection_error", str(e)
            )
        except Exception as e:
            return await self._handle_health_check_failure(
                service_name, "unknown_error", str(e)
            )
    
    def _determine_status(self, http_status: int, response_time: int) -> Literal['healthy', 'degraded', 'unhealthy']:
        """Determine service status based on response."""
        if http_status >= 500:
            return 'unhealthy'
        
        if response_time > ALERT_THRESHOLDS['response_time']['critical']:
            return 'degraded'
        
        if (http_status >= 400 or 
            response_time > ALERT_THRESHOLDS['response_time']['warning']):
            return 'degraded'
        
        return 'healthy'
    
    async def _handle_health_check_failure(
        self, 
        service_name: str, 
        error_type: str, 
        error_message: str
    ) -> HealthCheckResult:
        """Handle health check failure."""
        end_time = datetime.utcnow()
        
        result = HealthCheckResult(
            timestamp=end_time,
            status='unhealthy',
            response_time=0,
            http_status=0,
            error_message=f"{error_type}: {error_message}"
        )
        
        # Update service state
        await self._update_service_state(service_name, result)
        
        # Store result in Redis
        await self.redis_client.store_health_check(service_name, {
            "status": "unhealthy",
            "response_time": 0,
            "timestamp": end_time.isoformat(),
            "http_status": 0,
            "error_message": result.error_message,
            "consecutive_failures": self.service_states[service_name].consecutive_failures,
            "consecutive_successes": self.service_states[service_name].consecutive_successes
        })
        
        logger.warning(f"Health check failed for {service_name}: {error_message}")
        return result
    
    async def _update_service_state(self, service_name: str, result: HealthCheckResult):
        """Update internal service state."""
        service = self.service_states[service_name]
        
        # Update basic info
        service.status = result.status
        service.response_time = result.response_time
        service.last_checked = result.timestamp
        
        # Update consecutive counters
        if result.status == 'healthy':
            service.consecutive_successes += 1
            service.consecutive_failures = 0
        else:
            service.consecutive_failures += 1
            service.consecutive_successes = 0
        
        # Update version if available
        if result.service_version:
            service.version = result.service_version
        
        # Add to history (keep last 100)
        service.health_history.append(result)
        if len(service.health_history) > 100:
            service.health_history = service.health_history[-100:]
        
        # Calculate uptime
        service.uptime = self._calculate_uptime(service.health_history)
        
        # Update issues list for degraded services
        service.issues.clear()
        if result.status == 'degraded':
            if result.response_time > ALERT_THRESHOLDS['response_time']['warning']:
                service.issues.append(f"High response time ({result.response_time}ms)")
            if result.http_status >= 400:
                service.issues.append(f"HTTP error {result.http_status}")
        elif result.status == 'unhealthy':
            if result.error_message:
                service.issues.append(result.error_message)
            else:
                service.issues.append("Service unavailable")
        
        # Check for alerts
        await self._check_alerts(service_name, service)
    
    def _calculate_uptime(self, history: List[HealthCheckResult], hours: int = 24) -> float:
        """Calculate uptime percentage over specified period."""
        if not history:
            return 0.0
        
        # Filter to recent history (last N hours)
        cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
        recent_history = [
            r for r in history 
            if r.timestamp.timestamp() > cutoff_time
        ]
        
        if not recent_history:
            return 100.0
        
        healthy_count = len([r for r in recent_history if r.status == 'healthy'])
        total_count = len(recent_history)
        
        return (healthy_count / total_count) * 100
    
    async def _check_alerts(self, service_name: str, service: ServiceHealth):
        """Check if alerts should be triggered."""
        config = SERVICE_REGISTRY[service_name]
        
        # High response time alert
        if (service.response_time > ALERT_THRESHOLDS['response_time']['critical'] and
            service.consecutive_failures >= ALERT_THRESHOLDS['consecutive_failures']['critical']):
            
            alert = Alert(
                id=f"{service_name}-high-response-time-{int(datetime.utcnow().timestamp())}",
                type='high_response_time',
                severity='critical' if config['critical'] else 'medium',
                service=service_name,
                message=f"High response time: {service.response_time}ms",
                description=f"Service {service_name} response time is {service.response_time}ms",
                threshold=ALERT_THRESHOLDS['response_time']['critical'],
                current_value=service.response_time,
                triggered_at=datetime.utcnow(),
                status='active'
            )
            
            await self.redis_client.store_alert(alert.dict())
        
        # Service down alert
        if (service.status == 'unhealthy' and
            service.consecutive_failures >= ALERT_THRESHOLDS['consecutive_failures']['critical']):
            
            alert = Alert(
                id=f"{service_name}-service-down-{int(datetime.utcnow().timestamp())}",
                type='service_down',
                severity='critical',
                service=service_name,
                message=f"Service {service_name} is down",
                description=f"Service has failed {service.consecutive_failures} consecutive health checks",
                threshold=ALERT_THRESHOLDS['consecutive_failures']['critical'],
                current_value=service.consecutive_failures,
                triggered_at=datetime.utcnow(),
                status='active'
            )
            
            await self.redis_client.store_alert(alert.dict())
    
    async def get_all_service_health(self) -> List[ServiceHealth]:
        """Get health status of all services."""
        return list(self.service_states.values())
    
    async def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Get health status of a specific service."""
        return self.service_states.get(service_name)
    
    async def force_check_all(self) -> Dict[str, HealthCheckResult]:
        """Force immediate health check of all services."""
        results = {}
        tasks = []
        
        for service_name in SERVICE_REGISTRY.keys():
            task = asyncio.create_task(self.check_service_health(service_name))
            tasks.append((service_name, task))
        
        for service_name, task in tasks:
            try:
                result = await task
                if result:
                    results[service_name] = result
            except Exception as e:
                logger.error(f"Error in force check for {service_name}: {e}")
        
        return results