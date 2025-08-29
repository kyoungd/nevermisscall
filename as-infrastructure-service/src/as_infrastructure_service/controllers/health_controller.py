"""Health monitoring endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends

from ..models.health import ServiceHealth
from ..models.api import success_response, error_response
from ..services.health_checker import HealthChecker
from ..services.metrics_collector import MetricsCollector
from ..config.settings import settings, SERVICE_REGISTRY, CRITICAL_PATH_SERVICES

logger = logging.getLogger(__name__)


def create_health_router(health_checker: HealthChecker, metrics_collector: MetricsCollector) -> APIRouter:
    """Create health monitoring router."""
    
    router = APIRouter()
    
    @router.get("/health")
    async def get_health():
        """Overall infrastructure health status."""
        try:
            all_services = await health_checker.get_all_service_health()
            
            # Count services by status
            healthy_count = len([s for s in all_services if s.status == 'healthy'])
            degraded_count = len([s for s in all_services if s.status == 'degraded'])
            unhealthy_count = len([s for s in all_services if s.status == 'unhealthy'])
            unknown_count = len([s for s in all_services if s.status == 'unknown'])
            
            # Determine overall status
            if unhealthy_count > 0:
                overall_status = "degraded"
            elif degraded_count > 0:
                overall_status = "degraded"  
            else:
                overall_status = "healthy"
            
            # Calculate uptime (simplified)
            uptime_seconds = 86400  # Placeholder - would track actual uptime
            
            return {
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "version": settings.version,
                "uptime": uptime_seconds,
                "environment": settings.environment,
                "services": {
                    "total": len(all_services),
                    "healthy": healthy_count,
                    "unhealthy": unhealthy_count,
                    "unknown": unknown_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error in health endpoint: {e}")
            raise HTTPException(status_code=500, detail="Health check failed")
    
    @router.get("/health/services")
    async def get_services_health():
        """Detailed health status of all services."""
        try:
            all_services = await health_checker.get_all_service_health()
            
            services_data = []
            healthy_count = 0
            degraded_count = 0
            unhealthy_count = 0
            
            for service in all_services:
                service_data = {
                    "name": service.name,
                    "url": service.url,
                    "status": service.status,
                    "responseTime": service.response_time,
                    "lastChecked": service.last_checked.isoformat(),
                    "uptime": service.uptime,
                    "version": service.version
                }
                
                # Add issues if degraded/unhealthy
                if service.issues:
                    service_data["issues"] = service.issues
                
                services_data.append(service_data)
                
                # Count by status
                if service.status == 'healthy':
                    healthy_count += 1
                elif service.status == 'degraded':
                    degraded_count += 1
                elif service.status == 'unhealthy':
                    unhealthy_count += 1
            
            return {
                "services": services_data,
                "summary": {
                    "healthy": healthy_count,
                    "degraded": degraded_count,
                    "unhealthy": unhealthy_count,
                    "lastUpdated": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in services health endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to get services health")
    
    @router.get("/health/service/{service_name}")
    async def get_service_health(service_name: str):
        """Detailed health information for specific service."""
        try:
            service = await health_checker.get_service_health(service_name)
            if not service:
                raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
            
            # Get recent history (last 10 checks)
            recent_history = service.health_history[-10:] if service.health_history else []
            history_data = []
            
            for check in recent_history:
                history_data.append({
                    "timestamp": check.timestamp.isoformat(),
                    "status": check.status,
                    "responseTime": check.response_time
                })
            
            return {
                "service": {
                    "name": service.name,
                    "status": service.status,
                    "url": service.url,
                    "port": service.port,
                    "responseTime": service.response_time,
                    "lastChecked": service.last_checked.isoformat(),
                    "consecutiveFailures": service.consecutive_failures,
                    "uptimePercentage": service.uptime,
                    "healthHistory": history_data
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting service health for {service_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get service health")
    
    @router.get("/services")
    async def get_service_discovery():
        """List all registered services and their endpoints."""
        try:
            all_services = await health_checker.get_all_service_health()
            
            # Group services by category
            services_by_category = {
                "identity": {},
                "core": {},
                "external": {},
                "frontend": {}
            }
            
            for service in all_services:
                category = service.category
                if category not in services_by_category:
                    services_by_category[category] = {}
                
                services_by_category[category][service.name] = {
                    "url": service.url,
                    "healthEndpoint": service.health_endpoint,
                    "status": service.status,
                    "version": service.version
                }
            
            return {
                "services": services_by_category,
                "lastUpdated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in service discovery endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to get service discovery")
    
    @router.get("/services/dependencies")
    async def get_service_dependencies():
        """Service dependency graph and validation."""
        try:
            from ..config.settings import SERVICE_DEPENDENCIES
            
            all_services = await health_checker.get_all_service_health()
            service_status_map = {s.name: s.status for s in all_services}
            
            dependencies_info = {}
            healthy_dependencies = 0
            broken_dependencies = 0
            
            for service_name, deps in SERVICE_DEPENDENCIES.items():
                # Check dependency status
                dependency_statuses = []
                for dep in deps:
                    dep_status = service_status_map.get(dep, 'unknown')
                    dependency_statuses.append(dep_status)
                    
                    if dep_status == 'healthy':
                        healthy_dependencies += 1
                    else:
                        broken_dependencies += 1
                
                # Determine overall dependency status
                if all(status == 'healthy' for status in dependency_statuses):
                    dependency_status = 'healthy'
                elif any(status == 'unhealthy' for status in dependency_statuses):
                    dependency_status = 'unhealthy'
                else:
                    dependency_status = 'degraded'
                
                dependencies_info[service_name] = {
                    "dependsOn": deps,
                    "dependencyStatus": dependency_status,
                    "criticalPath": service_name in CRITICAL_PATH_SERVICES
                }
            
            return {
                "dependencies": dependencies_info,
                "criticalPath": CRITICAL_PATH_SERVICES,
                "healthyDependencies": healthy_dependencies,
                "brokenDependencies": broken_dependencies
            }
            
        except Exception as e:
            logger.error(f"Error in dependencies endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to get service dependencies")
    
    @router.get("/metrics")
    async def get_system_metrics():
        """Basic system and service metrics."""
        try:
            system_metrics = await metrics_collector.get_system_metrics()
            
            if not system_metrics:
                # Return empty metrics if none available
                system_metrics = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "uptime": 0,
                    "totalServices": len(SERVICE_REGISTRY),
                    "healthyServices": 0,
                    "averageResponseTime": 0,
                    "totalRequests": 0,
                    "errorRate": 0.0
                }
            
            # Get service-specific metrics
            services_metrics = {}
            for service_name in SERVICE_REGISTRY.keys():
                service_metrics = await metrics_collector.get_service_metrics(service_name)
                if service_metrics:
                    services_metrics[service_name] = service_metrics
            
            return {
                "system": system_metrics,
                "services": services_metrics
            }
            
        except Exception as e:
            logger.error(f"Error in metrics endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to get metrics")
    
    @router.get("/metrics/service/{service_name}")
    async def get_service_metrics(service_name: str):
        """Detailed metrics for specific service."""
        try:
            if service_name not in SERVICE_REGISTRY:
                raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
            
            service_metrics = await metrics_collector.get_service_metrics(service_name)
            
            if not service_metrics:
                raise HTTPException(status_code=404, detail=f"No metrics available for {service_name}")
            
            return {
                "service": service_name,
                "metrics": service_metrics
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting metrics for {service_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get service metrics")
    
    @router.get("/status/critical")
    async def get_critical_status():
        """Critical system status for alerts."""
        try:
            all_services = await health_checker.get_all_service_health()
            critical_services = {s.name: s for s in all_services if s.critical}
            
            # Determine critical status
            critical_issues = 0
            critical_services_status = {}
            
            for service_name, service in critical_services.items():
                critical_services_status[service_name] = service.status
                if service.status != 'healthy':
                    critical_issues += 1
            
            # Overall critical status
            if critical_issues == 0:
                overall_status = "operational"
            elif critical_issues <= len(critical_services) // 2:
                overall_status = "degraded"
            else:
                overall_status = "outage"
            
            # Get active alerts
            from ..services.redis_client import RedisClient
            redis_client = RedisClient()
            await redis_client.initialize()
            
            active_alerts = await redis_client.get_active_alerts()
            
            await redis_client.close()
            
            return {
                "critical": {
                    "status": overall_status,
                    "issueCount": critical_issues,
                    "criticalServices": critical_services_status
                },
                "alerts": active_alerts,
                "lastIncident": None  # Would track actual incidents
            }
            
        except Exception as e:
            logger.error(f"Error in critical status endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to get critical status")
    
    @router.get("/status/dashboard")
    async def get_dashboard_status():
        """Status dashboard data for web UI."""
        try:
            all_services = await health_checker.get_all_service_health()
            
            # Count services by status
            healthy_count = len([s for s in all_services if s.status == 'healthy'])
            degraded_count = len([s for s in all_services if s.status == 'degraded'])
            unhealthy_count = len([s for s in all_services if s.status == 'unhealthy'])
            
            # Determine overall status
            if unhealthy_count > 0:
                overall_status = "degraded"
            elif degraded_count > 0:
                overall_status = "degraded"
            else:
                overall_status = "healthy"
            
            # Calculate system uptime
            critical_services = [s for s in all_services if s.critical]
            system_uptime = min([s.uptime for s in critical_services]) if critical_services else 100.0
            
            # Get active alerts count
            from ..services.redis_client import RedisClient
            redis_client = RedisClient()
            await redis_client.initialize()
            
            active_alerts = await redis_client.get_active_alerts()
            
            await redis_client.close()
            
            # Create recent events (simplified)
            recent_events = []
            for service in all_services:
                if service.status != 'healthy':
                    recent_events.append({
                        "timestamp": service.last_checked.isoformat(),
                        "type": "service_degraded" if service.status == 'degraded' else "service_down",
                        "service": service.name,
                        "message": f"Service {service.status}: {', '.join(service.issues) if service.issues else 'Status changed'}"
                    })
            
            # Sort by timestamp and limit to recent
            recent_events.sort(key=lambda x: x["timestamp"], reverse=True)
            recent_events = recent_events[:5]
            
            return {
                "dashboard": {
                    "overallStatus": overall_status,
                    "systemUptime": system_uptime,
                    "activeAlerts": len(active_alerts),
                    "servicesSummary": {
                        "total": len(all_services),
                        "healthy": healthy_count,
                        "degraded": degraded_count,
                        "down": unhealthy_count
                    },
                    "recentEvents": recent_events,
                    "lastUpdated": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error in dashboard status endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to get dashboard status")
    
    return router