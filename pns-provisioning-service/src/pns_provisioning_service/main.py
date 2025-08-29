"""Main FastAPI application for Phone Number Service (PNS) Provisioning Service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import settings
from .services.database import DatabaseService
from .services.provisioning_service import ProvisioningService
from .controllers.provisioning_controller import create_provisioning_router
from .controllers.management_controller import create_management_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
database_service: DatabaseService = None
provisioning_service: ProvisioningService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global database_service, provisioning_service
    
    try:
        logger.info("Starting PNS Provisioning Service...")
        
        # Initialize database service
        database_service = DatabaseService()
        await database_service.initialize()
        logger.info("Database service initialized")
        
        # Initialize provisioning service
        provisioning_service = ProvisioningService(database_service)
        await provisioning_service.initialize()
        logger.info("Provisioning service initialized")
        
        logger.info("PNS Provisioning Service startup complete")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start PNS Provisioning Service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down PNS Provisioning Service...")
        if provisioning_service:
            await provisioning_service.close()
        if database_service:
            await database_service.close()
        logger.info("PNS Provisioning Service shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="PNS Provisioning Service",
        description="Phone Number Service (PNS) Provisioning Service - Handles phone number provisioning via Twilio",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        try:
            # Check database connection
            if database_service and await database_service.health_check():
                return {
                    "status": "healthy",
                    "service": "pns-provisioning-service",
                    "version": "1.0.0",
                    "database": "connected",
                    "twilio": "configured"
                }
            else:
                raise HTTPException(status_code=503, detail="Database connection failed")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
    
    # Ready check endpoint
    @app.get("/ready")
    async def ready_check():
        """Readiness check endpoint."""
        try:
            if not provisioning_service:
                raise HTTPException(status_code=503, detail="Provisioning service not initialized")
            
            # Test Twilio connectivity
            if not provisioning_service.twilio_client:
                raise HTTPException(status_code=503, detail="Twilio client not available")
            
            return {
                "status": "ready",
                "service": "pns-provisioning-service",
                "components": {
                    "database": "ready",
                    "twilio": "ready",
                    "provisioning": "ready"
                }
            }
        except Exception as e:
            logger.error(f"Ready check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")
    
    # Metrics endpoint
    @app.get("/metrics")
    async def get_metrics():
        """Get basic service metrics."""
        try:
            if not database_service:
                return {"error": "Database service not available"}
            
            # Get basic metrics from database
            phone_numbers_count = await database_service.get_total_phone_numbers()
            active_numbers_count = await database_service.get_active_phone_numbers_count()
            
            return {
                "service": "pns-provisioning-service",
                "metrics": {
                    "total_phone_numbers": phone_numbers_count,
                    "active_phone_numbers": active_numbers_count,
                    "provisioned_today": 0  # TODO: Implement daily count
                }
            }
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return {"error": f"Failed to collect metrics: {str(e)}"}
    
    return app


# Create the app instance
app = create_app()

# Register routers after app initialization
@app.on_event("startup")
async def setup_routes():
    """Setup routes after services are initialized."""
    global provisioning_service
    
    # Wait for provisioning service to be available
    if provisioning_service:
        # Add provisioning routes (internal service endpoints)
        provisioning_router = create_provisioning_router(provisioning_service)
        app.include_router(provisioning_router, prefix="/internal")
        
        # Add management routes (JWT authenticated endpoints)
        management_router = create_management_router(provisioning_service)
        app.include_router(management_router, prefix="/api/v1")
        
        logger.info("Routes registered successfully")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )