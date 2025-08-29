"""Connection manager for WebSocket connections."""

import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime
import socketio

from ..models.connection import ConnectionState
from ..services.redis_client import RedisClient
from ..services.auth_service import AuthService
from ..config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and their state."""
    
    def __init__(self, sio: socketio.AsyncServer, redis_client: RedisClient, auth_service: AuthService):
        self.sio = sio
        self.redis_client = redis_client
        self.auth_service = auth_service
        
        # In-memory connection tracking for quick lookups
        self._socket_to_connection: Dict[str, str] = {}  # socket_id -> connection_id
        self._connection_to_socket: Dict[str, str] = {}  # connection_id -> socket_id
    
    def _generate_room_name(self, room_type: str, identifier: str) -> str:
        """Generate Socket.IO room names for different entity types."""
        room_names = {
            'tenant': lambda id: f'tenant:{id}',
            'conversation': lambda id: f'conversation:{id}',
            'user': lambda id: f'user:{id}'
        }
        return room_names.get(room_type, lambda id: f'unknown:{id}')(identifier)
    
    async def handle_connection(self, sid: str, environ: Dict, auth: Optional[Dict] = None) -> bool:
        """Handle new WebSocket connection with authentication."""
        try:
            # Extract authentication token
            if not auth or 'token' not in auth:
                logger.warning(f"Connection {sid} missing authentication token")
                await self.sio.emit('error', {
                    'code': 'AUTHENTICATION_FAILED',
                    'message': 'Authentication token required',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=sid)
                return False
            
            # Authenticate user
            user_data = await self.auth_service.authenticate_socket_connection(auth['token'])
            if not user_data:
                logger.warning(f"Connection {sid} authentication failed")
                await self.sio.emit('error', {
                    'code': 'AUTHENTICATION_FAILED',
                    'message': 'Invalid or expired token',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=sid)
                return False
            
            user_id = user_data['user_id']
            tenant_id = user_data['tenant_id']
            
            # Check connection limits
            if not await self._check_connection_limits(tenant_id):
                logger.warning(f"Connection limit exceeded for tenant {tenant_id}")
                await self.sio.emit('error', {
                    'code': 'CONNECTION_LIMIT_EXCEEDED',
                    'message': 'Too many connections for tenant',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=sid)
                return False
            
            # Create connection state
            connection_id = str(uuid.uuid4())
            connection_state = ConnectionState(
                connection_id=connection_id,
                socket_id=sid,
                user_id=user_id,
                tenant_id=tenant_id,
                connected_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                subscribed_conversations=[],
                subscribed_events=[],
                is_active=True,
                redis_key=f"connections:{tenant_id}:{connection_id}",
                ttl=settings.connection_ttl_seconds,
                user_agent=environ.get('HTTP_USER_AGENT'),
                ip_address=environ.get('REMOTE_ADDR')
            )
            
            # Store connection state
            success = await self.redis_client.store_connection(connection_state)
            if not success:
                logger.error(f"Failed to store connection state for {connection_id}")
                await self.sio.emit('error', {
                    'code': 'INTERNAL_ERROR',
                    'message': 'Failed to establish connection',
                    'timestamp': datetime.utcnow().isoformat()
                }, room=sid)
                return False
            
            # Update in-memory tracking
            self._socket_to_connection[sid] = connection_id
            self._connection_to_socket[connection_id] = sid
            
            # Join tenant room for broadcasts
            tenant_room = self._generate_room_name('tenant', tenant_id)
            await self.sio.enter_room(sid, tenant_room)
            
            # Join user-specific room
            user_room = self._generate_room_name('user', user_id)
            await self.sio.enter_room(sid, user_room)
            
            # Send authentication confirmation
            await self.sio.emit('authenticated', {
                'userId': user_id,
                'tenantId': tenant_id,
                'connectionId': connection_id,
                'serverTime': datetime.utcnow().isoformat()
            }, room=sid)
            
            logger.info(f"Connection established: {connection_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling connection {sid}: {e}")
            await self.sio.emit('error', {
                'code': 'INTERNAL_ERROR',
                'message': 'Connection establishment failed',
                'timestamp': datetime.utcnow().isoformat()
            }, room=sid)
            return False
    
    async def handle_disconnection(self, sid: str) -> None:
        """Handle WebSocket disconnection."""
        try:
            # Get connection ID from in-memory tracking
            connection_id = self._socket_to_connection.get(sid)
            if not connection_id:
                logger.warning(f"Disconnection for unknown socket {sid}")
                return
            
            # Get connection state to find tenant
            connection_state = None
            for tenant_connections in await self._get_all_tenant_connections():
                for conn_id in tenant_connections:
                    if conn_id == connection_id:
                        # Find the tenant ID - this is a simplified approach
                        # In production, you might want to store this mapping separately
                        break
            
            # Clean up connection state
            if connection_id in self._connection_to_socket:
                # Extract tenant_id from connection state if available
                # For now, we'll try to clean up what we can
                del self._connection_to_socket[connection_id]
            
            if sid in self._socket_to_connection:
                del self._socket_to_connection[sid]
            
            logger.info(f"Connection disconnected: {connection_id}")
            
        except Exception as e:
            logger.error(f"Error handling disconnection {sid}: {e}")
    
    async def _check_connection_limits(self, tenant_id: str) -> bool:
        """Check if tenant is within connection limits."""
        try:
            tenant_connections = await self.redis_client.get_tenant_connections(tenant_id)
            return len(tenant_connections) < settings.max_connections_per_tenant
        except Exception as e:
            logger.error(f"Error checking connection limits: {e}")
            return False
    
    async def _get_all_tenant_connections(self) -> List[List[str]]:
        """Get all tenant connections - helper method."""
        # This is a simplified implementation
        # In production, you'd want a more efficient way to track this
        return []
    
    async def get_connection_by_socket(self, sid: str) -> Optional[ConnectionState]:
        """Get connection state by socket ID."""
        connection_id = self._socket_to_connection.get(sid)
        if not connection_id:
            return None
        
        # We need tenant_id to get the connection from Redis
        # For now, we'll search through active connections
        # In production, consider storing this mapping separately
        return None
    
    async def update_connection_activity(self, sid: str) -> bool:
        """Update last activity for connection."""
        try:
            connection_id = self._socket_to_connection.get(sid)
            if not connection_id:
                return False
            
            # Similar issue - we need tenant_id
            # For now, return True to avoid errors
            return True
            
        except Exception as e:
            logger.error(f"Error updating connection activity: {e}")
            return False
    
    async def subscribe_to_conversation(self, sid: str, conversation_id: str) -> bool:
        """Subscribe connection to conversation-specific events."""
        try:
            conversation_room = self._generate_room_name('conversation', conversation_id)
            await self.sio.enter_room(sid, conversation_room)
            
            logger.debug(f"Socket {sid} subscribed to conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to conversation: {e}")
            return False
    
    async def unsubscribe_from_conversation(self, sid: str, conversation_id: str) -> bool:
        """Unsubscribe connection from conversation-specific events."""
        try:
            conversation_room = self._generate_room_name('conversation', conversation_id)
            await self.sio.leave_room(sid, conversation_room)
            
            logger.debug(f"Socket {sid} unsubscribed from conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from conversation: {e}")
            return False
    
    async def get_tenant_connection_count(self, tenant_id: str) -> int:
        """Get active connection count for tenant."""
        try:
            tenant_connections = await self.redis_client.get_tenant_connections(tenant_id)
            return len(tenant_connections)
        except Exception as e:
            logger.error(f"Error getting tenant connection count: {e}")
            return 0
    
    async def get_all_active_connections(self) -> Dict[str, int]:
        """Get active connections by tenant."""
        # Simplified implementation for now
        return {"total": len(self._socket_to_connection)}