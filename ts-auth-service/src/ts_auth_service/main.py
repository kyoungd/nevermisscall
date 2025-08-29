"""Main FastAPI application for ts-auth-service."""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config.settings import settings
from .models.response import ErrorCode, error_response, success_response, validation_error_response
from .services.database import DatabaseService
from .services.auth_service import AuthService
from .services.token_service import token_service
from .controllers.auth_controller import create_auth_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
database_service: DatabaseService = None
auth_service: AuthService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global database_service, auth_service
    
    try:
        logger.info("Starting ts-auth-service...")
        
        # Initialize database service
        database_service = DatabaseService()
        if not await database_service.initialize():
            raise Exception("Failed to initialize database service")
        
        logger.info("Database service initialized")
        
        # Initialize auth service
        auth_service = AuthService(database_service, token_service)
        logger.info("Auth service initialized")
        
        # Start background cleanup task
        cleanup_task = asyncio.create_task(cleanup_expired_sessions())
        
        logger.info("ts-auth-service startup complete")
        yield
        
        # Cleanup
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        logger.error(f"Failed to start ts-auth-service: {e}")
        raise
    finally:
        logger.info("Shutting down ts-auth-service...")
        if database_service:
            await database_service.close()
        logger.info("ts-auth-service shutdown complete")


async def cleanup_expired_sessions():
    """Background task to clean up expired sessions."""
    while True:
        try:
            # Run cleanup every hour
            await asyncio.sleep(3600)
            
            if database_service:
                cleaned_count = await database_service.cleanup_expired_sessions()
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired sessions")
                    
        except asyncio.CancelledError:
            logger.info("Session cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="TypeScript Auth Service",
        description="User registration, login, and JWT token management for business owners",
        version=settings.version,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        try:
            # Check database connection
            db_healthy = False
            if database_service:
                db_healthy = await database_service.health_check()
            
            if db_healthy:
                return success_response({
                    "status": "healthy",
                    "service": settings.service_name,
                    "version": settings.version,
                    "database": "connected",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                return JSONResponse(
                    status_code=503,
                    content=error_response(
                        ErrorCode.SERVICE_UNAVAILABLE,
                        "Database connection failed"
                    )
                )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content=error_response(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    f"Service unhealthy: {str(e)}"
                )
            )
    
    # Ready check endpoint
    @app.get("/ready")
    async def ready_check():
        """Readiness check endpoint."""
        try:
            if not auth_service:
                return JSONResponse(
                    status_code=503,
                    content=error_response(
                        ErrorCode.SERVICE_UNAVAILABLE,
                        "Auth service not initialized"
                    )
                )
            
            return success_response({
                "status": "ready",
                "service": settings.service_name,
                "components": {
                    "database": "ready",
                    "auth": "ready",
                    "token": "ready"
                }
            })
        except Exception as e:
            logger.error(f"Ready check failed: {e}")
            return JSONResponse(
                status_code=503,
                content=error_response(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    f"Service not ready: {str(e)}"
                )
            )
    
    # Metrics endpoint
    @app.get("/metrics")
    async def get_metrics():
        """Get basic service metrics."""
        try:
            if not auth_service:
                return error_response(
                    ErrorCode.SERVICE_UNAVAILABLE,
                    "Auth service not available"
                )
            
            stats = await auth_service.get_service_stats()
            
            return success_response({
                "service": settings.service_name,
                "metrics": stats
            })
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return error_response(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Failed to collect metrics: {str(e)}"
            )
    
    # Global exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=400,
            content=validation_error_response(exc.errors())
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        
        # If detail is already a dict (from our error responses), return it
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )
        
        # Otherwise, create standard error response
        error_code = ErrorCode.INTERNAL_SERVER_ERROR
        if exc.status_code == 401:
            error_code = ErrorCode.UNAUTHORIZED_ACCESS
        elif exc.status_code == 403:
            error_code = ErrorCode.FORBIDDEN
        elif exc.status_code == 404:
            error_code = ErrorCode.USER_NOT_FOUND
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(error_code, str(exc.detail))
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_response(
                ErrorCode.INTERNAL_SERVER_ERROR,
                "Internal server error"
            )
        )
    
    return app


# Create the app instance
app = create_app()

# Register routers after app initialization
@app.on_event("startup")
async def setup_routes():
    """Setup routes after services are initialized."""
    global auth_service
    
    # Add authentication routes
    if auth_service:
        auth_router = create_auth_router(auth_service)
        app.include_router(auth_router)
        logger.info("Authentication routes registered successfully")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=(settings.environment == "development"),
        log_level=settings.log_level.lower()
    )