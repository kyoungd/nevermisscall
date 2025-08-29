"""Event broadcasting HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict, Any
from datetime import datetime

from ..models.events import BroadcastRequest, BroadcastResponse
from ..services.event_broadcaster import EventBroadcaster
from ..services.auth_service import AuthService


def create_broadcast_router(
    event_broadcaster: EventBroadcaster,
    auth_service: AuthService
) -> APIRouter:
    """Create event broadcasting router."""
    router = APIRouter(prefix="/broadcast", tags=["broadcasting"])
    
    @router.post("/", response_model=BroadcastResponse)
    async def broadcast_event(
        request: BroadcastRequest,
        x_service_key: str = Header(..., alias="x-service-key")
    ) -> BroadcastResponse:
        """Broadcast event to connected clients (internal endpoint)."""
        # Validate service key
        if not auth_service.validate_service_key(x_service_key):
            raise HTTPException(status_code=401, detail="Invalid service key")
        
        try:
            if request.tenant_id:
                # Broadcast to tenant
                result = await event_broadcaster.broadcast_to_tenant(
                    request.tenant_id,
                    request.event,
                    request.data
                )
            elif request.conversation_id:
                # Broadcast to conversation
                result = await event_broadcaster.broadcast_to_conversation(
                    request.conversation_id,
                    request.event,
                    request.data
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Either tenant_id or conversation_id must be provided"
                )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Broadcast failed: {result.get('error', 'Unknown error')}"
                )
            
            return BroadcastResponse(
                success=True,
                broadcast_sent=True,
                active_connections=result["broadcast"].get("connections_sent", 0),
                sent_at=datetime.utcnow()
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to broadcast event: {str(e)}")
    
    @router.post("/tenant/{tenant_id}")
    async def broadcast_to_tenant(
        tenant_id: str,
        event_data: Dict[str, Any],
        x_service_key: str = Header(..., alias="x-service-key")
    ):
        """Broadcast event to all tenant connections (internal endpoint)."""
        # Validate service key
        if not auth_service.validate_service_key(x_service_key):
            raise HTTPException(status_code=401, detail="Invalid service key")
        
        try:
            event = event_data.get("event")
            data = event_data.get("data")
            
            if not event or data is None:
                raise HTTPException(status_code=400, detail="Event and data are required")
            
            result = await event_broadcaster.broadcast_to_tenant(tenant_id, event, data)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Broadcast failed: {result.get('error', 'Unknown error')}"
                )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to broadcast to tenant: {str(e)}")
    
    @router.post("/conversation/{conversation_id}")
    async def broadcast_to_conversation(
        conversation_id: str,
        event_data: Dict[str, Any],
        x_service_key: str = Header(..., alias="x-service-key")
    ):
        """Broadcast event to specific conversation watchers (internal endpoint)."""
        # Validate service key
        if not auth_service.validate_service_key(x_service_key):
            raise HTTPException(status_code=401, detail="Invalid service key")
        
        try:
            event = event_data.get("event")
            data = event_data.get("data")
            
            if not event or data is None:
                raise HTTPException(status_code=400, detail="Event and data are required")
            
            result = await event_broadcaster.broadcast_to_conversation(conversation_id, event, data)
            
            if not result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Broadcast failed: {result.get('error', 'Unknown error')}"
                )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to broadcast to conversation: {str(e)}")
    
    return router