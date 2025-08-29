"""Main FastAPI application for as-infrastructure-service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import settings
from .services.redis_client import RedisClient
from .services.health_checker import HealthChecker
from .services.metrics_collector import MetricsCollector
from .controllers.health_controller import create_health_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
redis_client: RedisClient = None
health_checker: HealthChecker = None
metrics_collector: MetricsCollector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client, health_checker, metrics_collector
    
    # Startup
    logger.info(f"Starting {settings.service_name}")
    
    try:
        # Initialize Redis client
        redis_client = RedisClient()
        await redis_client.initialize()
        
        # Initialize health checker
        health_checker = HealthChecker(redis_client)
        await health_checker.initialize()
        
        # Initialize metrics collector
        metrics_collector = MetricsCollector(redis_client, health_checker)
        
        # Start monitoring
        await health_checker.start_monitoring()
        await metrics_collector.start_collection()
        
        logger.info(f"Service initialization completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down service")
        
        if metrics_collector:
            await metrics_collector.stop_collection()
        
        if health_checker:
            await health_checker.close()
        
        if redis_client:
            await redis_client.close()
        
        logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="as-infrastructure-service",
    description="Health monitoring and service discovery for NeverMissCall Phase 1",
    version=settings.version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on requirements
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def setup_routes():
    """Setup FastAPI routes after services are initialized."""
    # Health monitoring endpoints
    health_router = create_health_router(health_checker, metrics_collector)
    app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "status": "running",
        "version": settings.version,
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "as_infrastructure_service.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True
    )