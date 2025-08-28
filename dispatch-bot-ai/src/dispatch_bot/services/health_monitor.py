"""
Health monitoring service for external dependencies.
"""

import asyncio
import httpx
from typing import NamedTuple
from datetime import datetime


class HealthStatus(NamedTuple):
    """Overall health status"""
    overall_healthy: bool
    google_maps_healthy: bool 
    openai_healthy: bool
    recovery_detected: bool = False


class HealthMonitor:
    """Monitor health of external services"""
    
    def __init__(self):
        self.last_status = None
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def check_external_services(self) -> HealthStatus:
        """Check health of all external services"""
        google_maps_healthy = await self._check_google_maps()
        openai_healthy = await self._check_openai()
        
        overall_healthy = google_maps_healthy and openai_healthy
        
        # Check for recovery
        recovery_detected = False
        if self.last_status and not self.last_status.overall_healthy and overall_healthy:
            recovery_detected = True
        
        status = HealthStatus(
            overall_healthy=overall_healthy,
            google_maps_healthy=google_maps_healthy,
            openai_healthy=openai_healthy,
            recovery_detected=recovery_detected
        )
        
        self.last_status = status
        return status
    
    async def _check_google_maps(self) -> bool:
        """Check Google Maps API health"""
        try:
            # Simple connectivity check
            response = await self.client.get("https://maps.googleapis.com/")
            return response.status_code < 500
        except:
            return False
    
    async def _check_openai(self) -> bool:
        """Check OpenAI API health"""
        try:
            # Simple connectivity check  
            response = await self.client.get("https://api.openai.com/")
            return response.status_code < 500
        except:
            return False