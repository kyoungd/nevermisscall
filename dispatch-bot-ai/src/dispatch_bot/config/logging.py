"""
Logging configuration for Dispatch Bot AI API.
Provides structured JSON logging for production use.
"""

import logging
import sys
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger


def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to use JSON formatting (recommended for production)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )
    
    if json_logs:
        # Configure JSON logging for production
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        
        # Get the root logger and configure it
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(getattr(logging, level.upper()))
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FILENAME,
                           structlog.processors.CallsiteParameter.LINENO]
            ),
            structlog.dev.ConsoleRenderer()
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__ of the calling module)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class RequestLogger:
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def log_request(self, request: Any, response: Any = None) -> None:
        """
        Log an HTTP request and optionally its response.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object (optional)
        """
        # Extract request information
        request_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "client_ip": getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        }
        
        # Add response information if available
        if response:
            request_data.update({
                "status_code": getattr(response, 'status_code', None),
                "response_headers": dict(getattr(response, 'headers', {}))
            })
        
        self.logger.info("HTTP request", **request_data)


# Application logging constants
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        },
        "dispatch_bot": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        },
        "fastapi": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        }
    }
}