"""Socket.IO event handlers."""

import logging
from typing import Dict, Any, Optional
import socketio

from ..services.connection_manager import ConnectionManager
from ..services.event_broadcaster import EventBroadcaster
from ..services.auth_service import AuthService
from ..models.events import (
    TakeoverConversationData,
    SendMessageData, 
    UpdateLeadStatusData
)

logger = logging.getLogger(__name__)


def create_socket_handlers(
    sio: socketio.AsyncServer,
    connection_manager: ConnectionManager,
    event_broadcaster: EventBroadcaster,
    auth_service: AuthService
):
    """Create and register Socket.IO event handlers."""
    
    @sio.event
    async def connect(sid: str, environ: Dict, auth: Optional[Dict] = None):
        """Handle client connection."""
        logger.info(f"Client connecting: {sid}")
        
        # Handle authentication and connection setup
        success = await connection_manager.handle_connection(sid, environ, auth)
        
        if not success:
            logger.warning(f"Connection rejected: {sid}")
            await sio.disconnect(sid)
            return False
        
        return True
    
    @sio.event
    async def disconnect(sid: str):
        """Handle client disconnection."""
        logger.info(f"Client disconnecting: {sid}")
        await connection_manager.handle_disconnection(sid)
    
    @sio.event
    async def takeover_conversation(sid: str, data: Dict[str, Any]):
        """Handle conversation takeover by human."""
        try:
            # Validate data
            takeover_data = TakeoverConversationData(**data)
            
            # Update connection activity
            await connection_manager.update_connection_activity(sid)
            
            # Get connection to verify user has access
            connection_state = await connection_manager.get_connection_by_socket(sid)
            if not connection_state:
                await event_broadcaster.send_error(
                    sid, 
                    "UNAUTHORIZED_ACCESS", 
                    "Connection not found or expired"
                )
                return
            
            # TODO: Call as-call-service to handle takeover
            # For now, send confirmation
            confirmation_data = {
                "conversationId": takeover_data.conversation_id,
                "aiDeactivated": True,
                "messageId": f"msg-{sid}-takeover",
                "sentAt": "2024-01-01T10:02:00Z"  # TODO: Use actual timestamp
            }
            
            await event_broadcaster.send_takeover_confirmation(
                sid,
                takeover_data.conversation_id,
                confirmation_data
            )
            
            logger.info(f"Conversation takeover handled for {takeover_data.conversation_id}")
            
        except Exception as e:
            logger.error(f"Error handling takeover_conversation: {e}")
            await event_broadcaster.send_error(
                sid,
                "TAKEOVER_FAILED",
                f"Failed to process takeover: {str(e)}"
            )
    
    @sio.event
    async def send_message(sid: str, data: Dict[str, Any]):
        """Handle manual message sending."""
        try:
            # Validate data
            message_data = SendMessageData(**data)
            
            # Update connection activity
            await connection_manager.update_connection_activity(sid)
            
            # Get connection to verify user has access
            connection_state = await connection_manager.get_connection_by_socket(sid)
            if not connection_state:
                await event_broadcaster.send_error(
                    sid,
                    "UNAUTHORIZED_ACCESS",
                    "Connection not found or expired"
                )
                return
            
            # TODO: Call as-call-service to send message
            # For now, send confirmation
            confirmation_data = {
                "conversationId": message_data.conversation_id,
                "messageId": f"msg-{sid}-manual",
                "messageSid": f"SM{sid}manual",
                "status": "sent"
            }
            
            await event_broadcaster.send_message_confirmation(
                sid,
                message_data.conversation_id,
                confirmation_data
            )
            
            logger.info(f"Manual message sent for conversation {message_data.conversation_id}")
            
        except Exception as e:
            logger.error(f"Error handling send_message: {e}")
            await event_broadcaster.send_error(
                sid,
                "MESSAGE_SEND_FAILED",
                f"Failed to send message: {str(e)}"
            )
    
    @sio.event
    async def update_lead_status(sid: str, data: Dict[str, Any]):
        """Handle lead status update."""
        try:
            # Validate data
            lead_data = UpdateLeadStatusData(**data)
            
            # Update connection activity
            await connection_manager.update_connection_activity(sid)
            
            # Get connection to verify user has access
            connection_state = await connection_manager.get_connection_by_socket(sid)
            if not connection_state:
                await event_broadcaster.send_error(
                    sid,
                    "UNAUTHORIZED_ACCESS",
                    "Connection not found or expired"
                )
                return
            
            # TODO: Call as-call-service to update lead
            # For now, broadcast update
            await event_broadcaster.broadcast_lead_updated(
                connection_state.tenant_id,
                {
                    "leadId": lead_data.lead_id,
                    "status": lead_data.status,
                    "updatedAt": "2024-01-01T10:03:00Z"  # TODO: Use actual timestamp
                }
            )
            
            logger.info(f"Lead status updated: {lead_data.lead_id} -> {lead_data.status}")
            
        except Exception as e:
            logger.error(f"Error handling update_lead_status: {e}")
            await event_broadcaster.send_error(
                sid,
                "LEAD_UPDATE_FAILED",
                f"Failed to update lead: {str(e)}"
            )
    
    @sio.event
    async def subscribe_conversation(sid: str, data: Dict[str, Any]):
        """Handle conversation subscription."""
        try:
            conversation_id = data.get("conversationId")
            if not conversation_id:
                await event_broadcaster.send_error(
                    sid,
                    "INVALID_REQUEST",
                    "conversationId is required"
                )
                return
            
            # Subscribe to conversation events
            success = await connection_manager.subscribe_to_conversation(sid, conversation_id)
            
            if success:
                await sio.emit("conversation_subscribed", {
                    "conversationId": conversation_id,
                    "subscribed": True
                }, room=sid)
                
                logger.info(f"Socket {sid} subscribed to conversation {conversation_id}")
            else:
                await event_broadcaster.send_error(
                    sid,
                    "SUBSCRIPTION_FAILED",
                    "Failed to subscribe to conversation"
                )
                
        except Exception as e:
            logger.error(f"Error handling subscribe_conversation: {e}")
            await event_broadcaster.send_error(
                sid,
                "SUBSCRIPTION_FAILED",
                f"Failed to subscribe: {str(e)}"
            )
    
    @sio.event
    async def unsubscribe_conversation(sid: str, data: Dict[str, Any]):
        """Handle conversation unsubscription."""
        try:
            conversation_id = data.get("conversationId")
            if not conversation_id:
                await event_broadcaster.send_error(
                    sid,
                    "INVALID_REQUEST",
                    "conversationId is required"
                )
                return
            
            # Unsubscribe from conversation events
            success = await connection_manager.unsubscribe_from_conversation(sid, conversation_id)
            
            if success:
                await sio.emit("conversation_unsubscribed", {
                    "conversationId": conversation_id,
                    "subscribed": False
                }, room=sid)
                
                logger.info(f"Socket {sid} unsubscribed from conversation {conversation_id}")
            else:
                await event_broadcaster.send_error(
                    sid,
                    "UNSUBSCRIPTION_FAILED",
                    "Failed to unsubscribe from conversation"
                )
                
        except Exception as e:
            logger.error(f"Error handling unsubscribe_conversation: {e}")
            await event_broadcaster.send_error(
                sid,
                "UNSUBSCRIPTION_FAILED",
                f"Failed to unsubscribe: {str(e)}"
            )
    
    return sio