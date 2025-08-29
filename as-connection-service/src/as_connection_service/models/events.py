"""WebSocket event and API request models."""

from pydantic import BaseModel
from typing import Any, Optional, Dict, List
from datetime import datetime


class WebSocketEvent(BaseModel):
    """WebSocket event structure."""
    event: str
    data: Any
    timestamp: Optional[datetime] = None
    
    def model_post_init(self, __context):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BroadcastRequest(BaseModel):
    """Request to broadcast event to connected clients."""
    event: str
    data: Any
    tenant_id: Optional[str] = None
    conversation_id: Optional[str] = None


class AuthenticationData(BaseModel):
    """WebSocket authentication data."""
    token: str


class TakeoverConversationData(BaseModel):
    """Data for takeover conversation event."""
    conversation_id: str
    message: str


class SendMessageData(BaseModel):
    """Data for send message event."""
    conversation_id: str
    message: str


class UpdateLeadStatusData(BaseModel):
    """Data for update lead status event."""
    lead_id: str
    status: str
    notes: Optional[str] = None


class ConnectionStatusResponse(BaseModel):
    """Response for connection status endpoint."""
    status: str
    active_connections: Dict[str, Any]
    server_time: datetime


class BroadcastResponse(BaseModel):
    """Response for broadcast endpoint."""
    success: bool
    broadcast_sent: bool
    active_connections: int
    sent_at: datetime


class TenantConnectionsResponse(BaseModel):
    """Response for tenant connections endpoint."""
    connections: List[Dict[str, Any]]
    total_connections: int