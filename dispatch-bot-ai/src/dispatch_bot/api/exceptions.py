"""
Custom exception classes and error handlers for the Dispatch Bot API.
"""

from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
import structlog

from dispatch_bot.models.schemas import ErrorResponse

# Get logger instance
logger = structlog.get_logger(__name__)


class DispatchBotException(Exception):
    """Base exception for Dispatch Bot specific errors."""
    
    def __init__(self, message: str, error_code: str = "DISPATCH_BOT_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationException(DispatchBotException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", 422)
        self.details = details or {}


class BusinessRuleException(DispatchBotException):
    """Exception raised for business rule violations."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "BUSINESS_RULE_ERROR", 400)
        self.details = details or {}


class ExternalServiceException(DispatchBotException):
    """Exception raised when external services fail."""
    
    def __init__(self, message: str, service_name: str = "unknown"):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", 503)
        self.service_name = service_name


async def dispatch_bot_exception_handler(request: Request, exc: DispatchBotException) -> JSONResponse:
    """Handle custom Dispatch Bot exceptions."""
    logger.error(
        "Dispatch Bot exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=str(request.url)
    )
    
    error_response = ErrorResponse(
        code=exc.error_code,
        message=exc.message,
        details=getattr(exc, 'details', None)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_response.model_dump()}
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url)
    )
    
    # Map HTTP status codes to error codes
    error_code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
    }
    
    error_code = error_code_mapping.get(exc.status_code, "HTTP_ERROR")
    
    error_response = ErrorResponse(
        code=error_code,
        message=exc.detail or "An error occurred",
        details=None
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_response.model_dump()}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(
        "Request validation error",
        errors=exc.errors(),
        path=str(request.url)
    )
    
    # Format validation errors for client
    validation_errors = {}
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        validation_errors[field_path] = error["msg"]
    
    error_response = ErrorResponse(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=validation_errors
    )
    
    return JSONResponse(
        status_code=422,
        content={"error": error_response.model_dump()}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=str(request.url),
        exc_info=True
    )
    
    error_response = ErrorResponse(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details=None
    )
    
    return JSONResponse(
        status_code=500,
        content={"error": error_response.model_dump()}
    )


def setup_exception_handlers(app) -> None:
    """Setup all exception handlers for the FastAPI app."""
    
    # Custom exception handlers
    app.add_exception_handler(DispatchBotException, dispatch_bot_exception_handler)
    
    # Standard HTTP exception handler
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Validation exception handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Catch-all exception handler (must be last)
    app.add_exception_handler(Exception, general_exception_handler)