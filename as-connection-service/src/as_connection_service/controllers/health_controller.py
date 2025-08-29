"""Health check controller."""

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any

from ..services.redis_client import RedisClient
from ..services.auth_service import AuthService


def create_health_router(redis_client: RedisClient, auth_service: AuthService) -> APIRouter:
    """Create health check router."""
    router = APIRouter(prefix="/health", tags=["health"])
    
    @router.get("/")
    async def health_check() -> Dict[str, Any]:
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": "as-connection-service",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
    
    @router.get("/detailed")
    async def detailed_health_check() -> Dict[str, Any]:
        """Detailed health check including dependencies."""
        health_status = {
            "service": "as-connection-service",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "dependencies": {
                "redis": {"status": "unknown"},
                "auth_service": {"status": "unknown"}
            }
        }
        
        # Check Redis health
        try:
            redis_health = await redis_client.health_check()
            all_redis_healthy = all(redis_health.values())
            health_status["dependencies"]["redis"] = {
                "status": "healthy" if all_redis_healthy else "unhealthy",
                "details": redis_health
            }
        except Exception as e:
            health_status["dependencies"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check auth service health (simplified)
        try:
            # This is a basic check - in production you might want a dedicated health endpoint
            health_status["dependencies"]["auth_service"] = {
                "status": "assumed_healthy"  # Placeholder
            }
        except Exception as e:
            health_status["dependencies"]["auth_service"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall health
        dependency_issues = []
        for service, status in health_status["dependencies"].items():
            if status["status"] not in ["healthy", "assumed_healthy"]:
                dependency_issues.append(service)
        
        if dependency_issues:
            health_status["status"] = "degraded"
            health_status["issues"] = dependency_issues
        
        return health_status
    
    return router