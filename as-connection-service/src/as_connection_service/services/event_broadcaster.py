"""Event broadcasting service for real-time updates."""

import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import socketio

from ..models.events import WebSocketEvent, BroadcastRequest
from ..services.redis_client import RedisClient
from ..config import settings

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Handles broadcasting events to connected WebSocket clients."""
    
    def __init__(self, sio: socketio.AsyncServer, redis_client: RedisClient):
        self.sio = sio
        self.redis_client = redis_client
    
    def _generate_room_name(self, room_type: str, identifier: str) -> str:
        """Generate Socket.IO room names for different entity types."""
        room_names = {
            'tenant': lambda id: f'tenant:{id}',
            'conversation': lambda id: f'conversation:{id}',
            'user': lambda id: f'user:{id}'
        }
        return room_names.get(room_type, lambda id: f'unknown:{id}')(identifier)
    
    async def broadcast_to_tenant(self, tenant_id: str, event: str, data: Any) -> Dict[str, Any]:
        """Broadcast event to all connections for a specific tenant."""
        try:
            # Create WebSocket event
            ws_event = WebSocketEvent(event=event, data=data)
            
            # Generate event ID for tracking
            event_id = str(uuid.uuid4())
            
            # Store event in queue for reliability
            event_queue_data = {
                "id": event_id,
                "event": event,
                "tenant_id": tenant_id,
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            
            await self.redis_client.store_event(event_id, event_queue_data)
            
            # Get tenant room name
            tenant_room = self._generate_room_name('tenant', tenant_id)
            
            # Broadcast to tenant room
            await self.sio.emit(
                event,
                {
                    "event": event,
                    "data": data,
                    "timestamp": ws_event.timestamp.isoformat()
                },
                room=tenant_room
            )
            
            # Get connection count for response
            tenant_connections = await self.redis_client.get_tenant_connections(tenant_id)
            
            logger.info(f"Broadcasted event {event} to {len(tenant_connections)} connections in tenant {tenant_id}")
            
            return {
                "success": True,
                "broadcast": {
                    "event": event,
                    "tenant_id": tenant_id,
                    "connections_sent": len(tenant_connections),
                    "timestamp": ws_event.timestamp.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error broadcasting to tenant {tenant_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def broadcast_to_conversation(self, conversation_id: str, event: str, data: Any) -> Dict[str, Any]:
        """Broadcast event to connections watching a specific conversation."""
        try:
            # Create WebSocket event
            ws_event = WebSocketEvent(event=event, data=data)
            
            # Generate event ID for tracking
            event_id = str(uuid.uuid4())
            
            # Store event in queue
            event_queue_data = {
                "id": event_id,
                "event": event,
                "conversation_id": conversation_id,
                "data": data,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
            
            await self.redis_client.store_event(event_id, event_queue_data)
            
            # Get conversation room name
            conversation_room = self._generate_room_name('conversation', conversation_id)
            
            # Broadcast to conversation room
            await self.sio.emit(
                event,
                {
                    "event": event,
                    "data": data,
                    "timestamp": ws_event.timestamp.isoformat()
                },
                room=conversation_room
            )
            
            # Count connections in the room (simplified - Socket.IO doesn't provide easy room member count)
            connections_sent = 1  # Placeholder
            
            logger.info(f"Broadcasted event {event} to conversation {conversation_id}")
            
            return {
                "success": True,
                "broadcast": {
                    "event": event,
                    "conversation_id": conversation_id,
                    "connections_sent": connections_sent,
                    "timestamp": ws_event.timestamp.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error broadcasting to conversation {conversation_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def broadcast_call_incoming(self, tenant_id: str, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast incoming call event."""
        return await self.broadcast_to_tenant(tenant_id, "call_incoming", call_data)
    
    async def broadcast_call_missed(self, tenant_id: str, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast missed call event."""
        return await self.broadcast_to_tenant(tenant_id, "call_missed", call_data)
    
    async def broadcast_message_received(self, tenant_id: str, conversation_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast message received event."""
        # Broadcast to both tenant and conversation rooms
        tenant_result = await self.broadcast_to_tenant(tenant_id, "message_received", message_data)
        conversation_result = await self.broadcast_to_conversation(conversation_id, "message_received", message_data)
        
        return {
            "success": tenant_result["success"] and conversation_result["success"],
            "tenant_broadcast": tenant_result,
            "conversation_broadcast": conversation_result
        }
    
    async def broadcast_message_sent(self, tenant_id: str, conversation_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast message sent event."""
        # Broadcast to both tenant and conversation rooms
        tenant_result = await self.broadcast_to_tenant(tenant_id, "message_sent", message_data)
        conversation_result = await self.broadcast_to_conversation(conversation_id, "message_sent", message_data)
        
        return {
            "success": tenant_result["success"] and conversation_result["success"],
            "tenant_broadcast": tenant_result,
            "conversation_broadcast": conversation_result
        }
    
    async def broadcast_ai_activated(self, tenant_id: str, conversation_id: str, activation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast AI activation event."""
        # Broadcast to both tenant and conversation rooms
        tenant_result = await self.broadcast_to_tenant(tenant_id, "ai_activated", activation_data)
        conversation_result = await self.broadcast_to_conversation(conversation_id, "ai_activated", activation_data)
        
        return {
            "success": tenant_result["success"] and conversation_result["success"],
            "tenant_broadcast": tenant_result,
            "conversation_broadcast": conversation_result
        }
    
    async def broadcast_dashboard_status(self, tenant_id: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast dashboard status update."""
        return await self.broadcast_to_tenant(tenant_id, "dashboard_status", status_data)
    
    async def broadcast_lead_updated(self, tenant_id: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast lead status update."""
        return await self.broadcast_to_tenant(tenant_id, "lead_updated", lead_data)
    
    async def send_takeover_confirmation(self, sid: str, conversation_id: str, confirmation_data: Dict[str, Any]) -> bool:
        """Send takeover confirmation to specific connection."""
        try:
            await self.sio.emit(
                "takeover_confirmed",
                {
                    "event": "takeover_confirmed",
                    "data": confirmation_data,
                    "timestamp": datetime.utcnow().isoformat()
                },
                room=sid
            )
            
            logger.info(f"Sent takeover confirmation for conversation {conversation_id} to socket {sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending takeover confirmation: {e}")
            return False
    
    async def send_message_confirmation(self, sid: str, conversation_id: str, confirmation_data: Dict[str, Any]) -> bool:
        """Send message sent confirmation to specific connection."""
        try:
            await self.sio.emit(
                "message_sent_confirmation",
                {
                    "event": "message_sent_confirmation",
                    "data": confirmation_data,
                    "timestamp": datetime.utcnow().isoformat()
                },
                room=sid
            )
            
            logger.info(f"Sent message confirmation for conversation {conversation_id} to socket {sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message confirmation: {e}")
            return False
    
    async def send_error(self, sid: str, error_code: str, message: str) -> bool:
        """Send error event to specific connection."""
        try:
            await self.sio.emit(
                "error",
                {
                    "event": "error",
                    "data": {
                        "code": error_code,
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                room=sid
            )
            
            logger.warning(f"Sent error {error_code} to socket {sid}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
            return False