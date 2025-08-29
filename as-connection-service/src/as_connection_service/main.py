"""Main FastAPI application for as-connection-service."""

import logging
import socketio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .services.redis_client import RedisClient
from .services.auth_service import AuthService
from .services.connection_manager import ConnectionManager
from .services.event_broadcaster import EventBroadcaster
from .controllers.health_controller import create_health_router
from .controllers.connection_controller import create_connection_router
from .controllers.broadcast_controller import create_broadcast_router
from .utils.socket_handlers import create_socket_handlers

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
redis_client: RedisClient = None
auth_service: AuthService = None
connection_manager: ConnectionManager = None
event_broadcaster: EventBroadcaster = None
sio: socketio.AsyncServer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client, auth_service, connection_manager, event_broadcaster, sio
    
    # Startup
    logger.info(f"Starting {settings.service_name}")
    
    try:
        # Initialize Redis client
        redis_client = RedisClient()
        await redis_client.initialize()
        
        # Initialize auth service
        auth_service = AuthService()
        
        # Create Socket.IO server
        sio = socketio.AsyncServer(
            cors_allowed_origins=settings.cors_origins,
            async_mode='asgi',
            ping_timeout=settings.heartbeat_timeout_ms / 1000,
            ping_interval=settings.heartbeat_interval_ms / 1000,
            max_http_buffer_size=64 * 1024,  # 64KB
            logger=False,
            engineio_logger=False
        )
        
        # Initialize services
        connection_manager = ConnectionManager(sio, redis_client, auth_service)
        event_broadcaster = EventBroadcaster(sio, redis_client)
        
        # Register Socket.IO handlers
        create_socket_handlers(sio, connection_manager, event_broadcaster, auth_service)
        
        logger.info(f"Service initialization completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down service")
        
        if redis_client:
            await redis_client.close()
        
        if auth_service:
            await auth_service.close()
        
        logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="as-connection-service",
    description="WebSocket management for real-time dashboard updates and live communication",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path="/socket.io/"
)


@app.on_event("startup")
async def setup_routes():
    """Setup FastAPI routes after services are initialized."""
    # Health endpoints
    health_router = create_health_router(redis_client, auth_service)
    app.include_router(health_router)
    
    # Connection management endpoints
    connection_router = create_connection_router(connection_manager, redis_client, auth_service)
    app.include_router(connection_router)
    
    # Broadcasting endpoints
    broadcast_router = create_broadcast_router(event_broadcaster, auth_service)
    app.include_router(broadcast_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "status": "running",
        "version": "1.0.0",
        "websocket_path": "/socket.io/"
    }


# Export the Socket.IO ASGI app as the main app
main_app = socket_app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "as_connection_service.main:main_app",
        host="0.0.0.0",
        port=settings.port,
        reload=True
    )