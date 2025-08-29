"""HTTP client utilities for service-to-service communication."""

import asyncio
from typing import Any, Dict, Optional, Union

import httpx
from fastapi import HTTPException

from ..config import settings
from .shared_integration import logger


class ServiceClient:
    """HTTP client for communicating with other services."""
    
    def __init__(self):
        self.timeout = httpx.Timeout(settings.request_timeout)
        self.headers = {
            "Content-Type": "application/json",
            "x-service-key": settings.internal_service_key,
        }
    
    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to external service."""
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        
        request_timeout = timeout or settings.request_timeout
        
        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=request_headers
                )
                
                if response.status_code >= 400:
                    logger.error(
                        f"Service request failed",
                        method=method,
                        url=url,
                        status_code=response.status_code,
                        response=response.text
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Service request failed: {response.text}"
                    )
                
                return response.json()
                
        except httpx.TimeoutException:
            logger.error(f"Service request timeout", method=method, url=url)
            raise HTTPException(status_code=504, detail="Service request timeout")
        except httpx.RequestError as e:
            logger.error(f"Service request error", method=method, url=url, error=str(e))
            raise HTTPException(status_code=502, detail="Service unavailable")
    
    async def send_sms_via_twilio_server(
        self,
        to_phone: str,
        from_phone: str,
        message: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Send SMS via twilio-server."""
        url = f"{settings.twilio_server_url}/internal/sms/send"
        data = {
            "to": to_phone,
            "from": from_phone,
            "body": message,
            "tenantId": tenant_id,
        }
        
        logger.info(
            "Sending SMS via twilio-server",
            to=to_phone,
            from_phone=from_phone,
            tenant_id=tenant_id
        )
        
        return await self._make_request("POST", url, data)
    
    async def process_ai_conversation(
        self,
        conversation_id: str,
        message_content: str,
        conversation_history: list,
        tenant_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process conversation through dispatch-bot-ai."""
        url = f"{settings.dispatch_ai_url}/dispatch/process"
        data = {
            "conversationId": conversation_id,
            "messageContent": message_content,
            "conversationHistory": conversation_history,
            "tenantContext": tenant_context,
        }
        
        logger.info(
            "Processing conversation via dispatch-bot-ai",
            conversation_id=conversation_id,
            tenant_id=tenant_context.get("tenantId")
        )
        
        return await self._make_request("POST", url, data)
    
    async def validate_tenant_and_service_area(
        self,
        tenant_id: str,
        customer_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate tenant and service area via ts-tenant-service."""
        url = f"{settings.ts_tenant_service_url}/internal/tenants/{tenant_id}/validate"
        data = {}
        if customer_address:
            data["customerAddress"] = customer_address
        
        logger.info(
            "Validating tenant and service area",
            tenant_id=tenant_id,
            has_address=bool(customer_address)
        )
        
        return await self._make_request("POST", url, data)
    
    async def broadcast_realtime_event(
        self,
        tenant_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Broadcast real-time event via as-connection-service."""
        url = f"{settings.as_connection_service_url}/internal/events/broadcast"
        data = {
            "tenantId": tenant_id,
            "eventType": event_type,
            "eventData": event_data,
            "timestamp": asyncio.get_event_loop().time(),
        }
        
        logger.info(
            "Broadcasting real-time event",
            tenant_id=tenant_id,
            event_type=event_type
        )
        
        try:
            await self._make_request("POST", url, data)
        except Exception as e:
            # Don't fail the main operation if real-time broadcast fails
            logger.warning(
                "Failed to broadcast real-time event",
                tenant_id=tenant_id,
                event_type=event_type,
                error=str(e)
            )


# Global client instance
service_client = ServiceClient()