"""Metrics collection and aggregation service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..models.health import ServiceMetrics, SystemMetrics
from ..config.settings import SERVICE_REGISTRY
from .redis_client import RedisClient
from .health_checker import HealthChecker

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates service and system metrics."""
    
    def __init__(self, redis_client: RedisClient, health_checker: HealthChecker):
        self.redis_client = redis_client
        self.health_checker = health_checker
        self.collection_task: Optional[asyncio.Task] = None
    
    async def start_collection(self, interval_seconds: int = 60):
        """Start periodic metrics collection."""
        self.collection_task = asyncio.create_task(
            self._collect_metrics_periodically(interval_seconds)
        )
        logger.info(f"Started metrics collection with {interval_seconds}s interval")
    
    async def stop_collection(self):
        """Stop metrics collection."""
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped metrics collection")
    
    async def _collect_metrics_periodically(self, interval: int):
        """Periodic metrics collection task."""
        while True:
            try:
                await self.collect_all_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Metrics collection cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(interval)
    
    async def collect_all_metrics(self):
        """Collect metrics for all services and system."""
        # Collect service metrics
        for service_name in SERVICE_REGISTRY.keys():
            await self.collect_service_metrics(service_name)
        
        # Collect system metrics
        await self.collect_system_metrics()
        
        logger.debug("Completed metrics collection cycle")
    
    async def collect_service_metrics(self, service_name: str) -> Optional[ServiceMetrics]:
        """Collect metrics for a specific service."""
        try:
            service_health = self.health_checker.service_states.get(service_name)
            if not service_health:
                return None
            
            # Calculate response time metrics from history
            response_times = [
                r.response_time for r in service_health.health_history 
                if r.response_time > 0
            ]
            
            if response_times:
                response_time_metrics = {
                    "current": service_health.response_time,
                    "average": sum(response_times) / len(response_times),
                    "p95": self._calculate_percentile(response_times, 95),
                    "p99": self._calculate_percentile(response_times, 99)
                }
            else:
                response_time_metrics = {
                    "current": 0,
                    "average": 0,
                    "p95": 0,
                    "p99": 0
                }
            
            # Calculate request metrics (simplified - would need actual request data)
            total_checks = len(service_health.health_history)
            error_count = len([r for r in service_health.health_history if r.status != 'healthy'])
            
            request_metrics = {
                "total": total_checks,
                "perMinute": self._calculate_requests_per_minute(service_health.health_history),
                "errorCount": error_count,
                "errorRate": (error_count / total_checks) if total_checks > 0 else 0.0
            }
            
            # Calculate availability metrics
            availability_metrics = {
                "uptime": service_health.uptime,
                "downtimeMinutes": self._calculate_downtime_minutes(service_health.health_history),
                "mtbf": self._calculate_mtbf(service_health.health_history),
                "mttr": self._calculate_mttr(service_health.health_history)
            }
            
            metrics = ServiceMetrics(
                service_name=service_name,
                timestamp=datetime.utcnow(),
                response_time=response_time_metrics,
                requests=request_metrics,
                availability=availability_metrics
            )
            
            # Store in Redis
            await self.redis_client.store_service_metrics(service_name, metrics.dict())
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for {service_name}: {e}")
            return None
    
    async def collect_system_metrics(self) -> Optional[SystemMetrics]:
        """Collect overall system metrics."""
        try:
            all_services = await self.health_checker.get_all_service_health()
            
            # Count services by status
            healthy_services = len([s for s in all_services if s.status == 'healthy'])
            degraded_services = len([s for s in all_services if s.status == 'degraded'])
            unhealthy_services = len([s for s in all_services if s.status == 'unhealthy'])
            
            # Calculate average response times
            all_response_times = []
            total_requests = 0
            total_errors = 0
            
            for service in all_services:
                response_times = [r.response_time for r in service.health_history if r.response_time > 0]
                all_response_times.extend(response_times)
                
                total_requests += len(service.health_history)
                total_errors += len([r for r in service.health_history if r.status != 'healthy'])
            
            # Calculate system metrics
            avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
            p95_response_time = self._calculate_percentile(all_response_times, 95) if all_response_times else 0
            p99_response_time = self._calculate_percentile(all_response_times, 99) if all_response_times else 0
            
            error_rate = (total_errors / total_requests) if total_requests > 0 else 0.0
            
            # Calculate system uptime (based on critical services)
            critical_services = [s for s in all_services if s.critical]
            system_uptime = min([s.uptime for s in critical_services]) if critical_services else 100.0
            
            # Count active alerts
            active_alerts = await self.redis_client.get_active_alerts()
            
            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                total_services=len(all_services),
                healthy_services=healthy_services,
                degraded_services=degraded_services,
                unhealthy_services=unhealthy_services,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                total_requests=total_requests,
                requests_per_minute=self._calculate_system_requests_per_minute(all_services),
                error_rate=error_rate,
                system_uptime=system_uptime,
                alert_count=len(active_alerts)
            )
            
            # Store in Redis
            await self.redis_client.store_system_metrics(metrics.dict())
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return None
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        
        if index >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[index]
    
    def _calculate_requests_per_minute(self, history: List) -> float:
        """Calculate requests per minute from health check history."""
        # Simplified calculation based on health checks
        # In real implementation, would use actual request data
        if not history:
            return 0.0
        
        # Get checks from last minute
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_checks = [
            h for h in history 
            if h.timestamp > one_minute_ago
        ]
        
        return float(len(recent_checks))
    
    def _calculate_system_requests_per_minute(self, services: List) -> int:
        """Calculate system-wide requests per minute."""
        total_rpm = 0
        for service in services:
            total_rpm += self._calculate_requests_per_minute(service.health_history)
        return int(total_rpm)
    
    def _calculate_downtime_minutes(self, history: List) -> float:
        """Calculate total downtime in minutes from history."""
        if not history:
            return 0.0
        
        # Find periods of downtime
        downtime_periods = []
        current_downtime_start = None
        
        for check in sorted(history, key=lambda x: x.timestamp):
            if check.status == 'unhealthy':
                if current_downtime_start is None:
                    current_downtime_start = check.timestamp
            else:
                if current_downtime_start is not None:
                    downtime_periods.append({
                        'start': current_downtime_start,
                        'end': check.timestamp
                    })
                    current_downtime_start = None
        
        # Calculate total downtime
        total_downtime = 0.0
        for period in downtime_periods:
            duration = (period['end'] - period['start']).total_seconds() / 60
            total_downtime += duration
        
        return total_downtime
    
    def _calculate_mtbf(self, history: List) -> float:
        """Calculate Mean Time Between Failures (minutes)."""
        if not history:
            return 0.0
        
        # Simplified MTBF calculation
        failures = [h for h in history if h.status == 'unhealthy']
        if len(failures) <= 1:
            return 0.0
        
        # Calculate time between failures
        failure_intervals = []
        for i in range(1, len(failures)):
            interval = (failures[i].timestamp - failures[i-1].timestamp).total_seconds() / 60
            failure_intervals.append(interval)
        
        return sum(failure_intervals) / len(failure_intervals) if failure_intervals else 0.0
    
    def _calculate_mttr(self, history: List) -> float:
        """Calculate Mean Time To Recovery (minutes)."""
        if not history:
            return 0.0
        
        # Find failure/recovery pairs
        recovery_times = []
        failure_start = None
        
        for check in sorted(history, key=lambda x: x.timestamp):
            if check.status == 'unhealthy' and failure_start is None:
                failure_start = check.timestamp
            elif check.status == 'healthy' and failure_start is not None:
                recovery_time = (check.timestamp - failure_start).total_seconds() / 60
                recovery_times.append(recovery_time)
                failure_start = None
        
        return sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
    
    async def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get latest metrics for a service."""
        return await self.redis_client.get_service_metrics(service_name)
    
    async def get_system_metrics(self) -> Optional[Dict[str, Any]]:
        """Get latest system metrics."""
        return await self.redis_client.get_system_metrics()