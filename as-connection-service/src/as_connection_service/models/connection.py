"""Connection and event queue models."""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class ConnectionState(BaseModel):
    """WebSocket connection state stored in Redis."""
    connection_id: str
    socket_id: str
    user_id: str
    tenant_id: str
    
    # Connection details
    connected_at: datetime
    last_activity: datetime
    
    # Subscriptions
    subscribed_conversations: List[str]
    subscribed_events: List[str]
    
    # Status
    is_active: bool
    
    # Metadata stored in Redis
    redis_key: str
    ttl: int  # seconds
    
    # Optional fields
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class EventQueueItem(BaseModel):
    """Event queue item for reliable event delivery."""
    id: str
    event: str
    tenant_id: str
    data: Any
    
    # Delivery
    target_connections: List[str]
    delivered_connections: List[str]
    failed_connections: List[str]
    
    # Timing
    created_at: datetime
    expires_at: datetime
    
    # Retry logic
    retry_count: int
    max_retries: int
    
    # Optional fields
    conversation_id: Optional[str] = None