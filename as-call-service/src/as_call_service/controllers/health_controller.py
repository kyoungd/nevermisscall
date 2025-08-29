"""Health check controller for service monitoring."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from ..utils import logger, health_check
from ..config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Dict[str, Any])
async def get_health() -> Dict[str, Any]:
    """Health check endpoint for service monitoring."""
    try:
        # Check database health
        db_healthy = await health_check()
        
        # Check service dependencies (simplified for now)
        services_health = {
            "database": "healthy" if db_healthy else "unhealthy",
            "twilio_server": "unknown",  # Would need actual health check
            "dispatch_ai": "unknown",    # Would need actual health check
            "ts_tenant_service": "unknown",  # Would need actual health check
        }
        
        # Determine overall status
        overall_healthy = all(
            status in ["healthy", "unknown"] 
            for status in services_health.values()
        )
        
        health_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "services": services_health,
            "uptime_seconds": 0,  # Would need to track actual uptime
            "service_name": settings.service_name,
            "port": settings.port,
        }
        
        if not overall_healthy:
            # Return 503 if unhealthy
            raise HTTPException(status_code=503, detail=health_data)
        
        return health_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.get("/health/ready", response_model=Dict[str, Any])
async def get_readiness() -> Dict[str, Any]:
    """Readiness check endpoint for deployment health."""
    try:
        # Check if service is ready to handle requests
        db_healthy = await health_check()
        
        if not db_healthy:
            raise HTTPException(
                status_code=503,
                detail={
                    "ready": False,
                    "reason": "database_unavailable",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat(),
            "service_name": settings.service_name,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "reason": "service_error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/health/live", response_model=Dict[str, Any])
async def get_liveness() -> Dict[str, Any]:
    """Liveness check endpoint for container health."""
    try:
        # Basic liveness check - if we can respond, we're alive
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat(),
            "service_name": settings.service_name,
        }
        
    except Exception as e:
        logger.error("Liveness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "alive": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )