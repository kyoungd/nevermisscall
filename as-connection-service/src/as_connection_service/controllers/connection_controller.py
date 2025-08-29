"""Connection management HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models.events import ConnectionStatusResponse, TenantConnectionsResponse
from ..services.connection_manager import ConnectionManager
from ..services.redis_client import RedisClient
from ..services.auth_service import AuthService
from ..utils.auth import validate_service_key, get_current_user


def create_connection_router(
    connection_manager: ConnectionManager,
    redis_client: RedisClient,
    auth_service: AuthService
) -> APIRouter:
    """Create connection management router."""
    router = APIRouter(prefix="/connections", tags=["connections"])
    
    @router.get("/status", response_model=ConnectionStatusResponse)
    async def get_connection_status(
        current_user: Dict = Depends(lambda: get_current_user(auth_service))
    ) -> ConnectionStatusResponse:
        """Get connection service status for authenticated user."""
        try:
            # Get all active connections
            active_connections = await connection_manager.get_all_active_connections()
            
            return ConnectionStatusResponse(
                status="healthy",
                active_connections=active_connections,
                server_time=datetime.utcnow()
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get connection status: {str(e)}")
    
    @router.get("/tenant/{tenant_id}", response_model=TenantConnectionsResponse)
    async def get_tenant_connections(
        tenant_id: str,
        x_service_key: str = Header(..., alias="x-service-key")
    ) -> TenantConnectionsResponse:
        """Get active connections for a specific tenant (internal endpoint)."""
        # Validate service key
        if not auth_service.validate_service_key(x_service_key):
            raise HTTPException(status_code=401, detail="Invalid service key")
        
        try:
            # Get tenant connections from Redis
            connection_ids = await redis_client.get_tenant_connections(tenant_id)
            
            # Build connection details
            connections = []
            for conn_id in connection_ids:
                connection_state = await redis_client.get_connection(tenant_id, conn_id)
                if connection_state:
                    connections.append({
                        "connectionId": connection_state.connection_id,
                        "userId": connection_state.user_id,
                        "connectedAt": connection_state.connected_at.isoformat(),
                        "lastActivity": connection_state.last_activity.isoformat()
                    })
            
            return TenantConnectionsResponse(
                connections=connections,
                total_connections=len(connections)
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get tenant connections: {str(e)}")
    
    return router


def get_current_user(auth_service: AuthService):
    """Dependency to get current authenticated user."""
    # This would be implemented to extract and validate JWT from Authorization header
    # For now, return a placeholder
    async def _get_current_user(authorization: Optional[str] = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization.replace("Bearer ", "")
        user_data = await auth_service.authenticate_socket_connection(token)
        
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return user_data
    
    return _get_current_user