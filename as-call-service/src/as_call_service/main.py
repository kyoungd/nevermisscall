"""Main FastAPI application for as-call-service."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .controllers import (
    call_router,
    conversation_router,
    lead_router,
    health_router,
)
from .utils import logger, init_database, errorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info(
        "Starting as-call-service",
        service_name=settings.service_name,
        port=settings.port,
        debug=settings.debug
    )
    
    try:
        # Initialize database connection
        await init_database(settings.database_url)
        logger.info("Database connection initialized")
        
        # Additional startup tasks could go here
        # e.g., warming up external service connections
        
        logger.info("as-call-service startup completed")
        
    except Exception as e:
        logger.error("Failed to start as-call-service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down as-call-service")
    
    try:
        # Cleanup tasks could go here
        # e.g., closing database connections, cleanup background tasks
        
        logger.info("as-call-service shutdown completed")
        
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="AS Call Service",
    description="NeverMissCall AS Call Service - Core business logic hub for call processing, conversation management, and AI coordination",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)


# Middleware
if settings.debug:
    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = asyncio.get_event_loop().time()
    
    # Log request
    logger.info(
        "HTTP request received",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else "unknown"
    )
    
    try:
        response = await call_next(request)
        
        # Calculate response time
        process_time = asyncio.get_event_loop().time() - start_time
        
        # Log response
        logger.info(
            "HTTP response sent",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2)
        )
        
        return response
        
    except Exception as e:
        # Log error
        process_time = asyncio.get_event_loop().time() - start_time
        logger.error(
            "HTTP request error",
            method=request.method,
            url=str(request.url),
            error=str(e),
            process_time_ms=round(process_time * 1000, 2)
        )
        raise


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Global error handling middleware."""
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        # Let FastAPI handle HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(
            "Unhandled exception in request",
            method=request.method,
            url=str(request.url),
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Return generic error response
        return JSONResponse(
            status_code=500,
            content=errorResponse(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred",
                {"timestamp": asyncio.get_event_loop().time()}
            )
        )


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        method=request.method,
        url=str(request.url),
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=errorResponse(
            f"HTTP_{exc.status_code}",
            exc.detail,
            {"path": str(request.url)}
        )
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors."""
    logger.warning(
        "Validation error",
        method=request.method,
        url=str(request.url),
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=400,
        content=errorResponse(
            "VALIDATION_ERROR",
            str(exc),
            {"path": str(request.url)}
        )
    )


# Include routers
app.include_router(health_router)
app.include_router(call_router)
app.include_router(conversation_router)
app.include_router(lead_router)


@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "as-call-service",
        "version": "1.0.0",
        "description": "NeverMissCall AS Call Service - Core business logic hub",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "calls": "/calls",
            "conversations": "/conversations",
            "leads": "/leads",
        }
    }


@app.get("/info", response_model=Dict[str, Any])
async def service_info():
    """Service information endpoint."""
    return {
        "service_name": settings.service_name,
        "version": "1.0.0",
        "port": settings.port,
        "debug": settings.debug,
        "environment": "development" if settings.is_development else "production",
        "features": {
            "call_processing": True,
            "conversation_management": True,
            "ai_coordination": True,
            "lead_management": True,
            "service_area_validation": settings.service_area_validation_enabled,
        },
        "limits": {
            "ai_takeover_delay_seconds": settings.ai_takeover_delay_seconds,
            "message_timeout_minutes": settings.message_timeout_minutes,
            "max_conversation_messages": settings.max_conversation_messages,
        }
    }


# Main entry point
if __name__ == "__main__":
    # Configure logging
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if not settings.log_json else None
    )
    
    # Run server
    uvicorn.run(
        "as_call_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )