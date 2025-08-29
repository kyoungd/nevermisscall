"""Integration utilities for the shared library."""

import sys
import os
from pathlib import Path

# Add shared library to Python path
shared_path = Path(__file__).parent.parent.parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

try:
    from shared.database import DatabaseConnection, init_database, query, health_check
    from shared.config import getCommonConfig, SERVICE_PORTS
    from shared.utils.logger import logger
    from shared.utils.validation import validateRequired
    from shared.models.api import ApiResponse, successResponse, errorResponse
    from shared.models.exceptions import (
        ValidationError,
        DatabaseError,
        ServiceError,
        AuthenticationError,
    )
except ImportError as e:
    # Fallback for development/testing when shared library isn't available
    print(f"Warning: Could not import shared library: {e}")
    print("Using fallback implementations")
    
    import logging
    
    class FallbackLogger:
        def __init__(self):
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        def info(self, msg, **kwargs):
            self.logger.info(msg, extra=kwargs)
        
        def error(self, msg, **kwargs):
            self.logger.error(msg, extra=kwargs)
        
        def warning(self, msg, **kwargs):
            self.logger.warning(msg, extra=kwargs)
        
        def debug(self, msg, **kwargs):
            self.logger.debug(msg, extra=kwargs)
    
    logger = FallbackLogger()
    
    def validateRequired(value, field_name):
        if not value:
            raise ValueError(f"{field_name} is required")
    
    def successResponse(data, message="Success"):
        return {"success": True, "data": data, "message": message}
    
    def errorResponse(error_code, message, details=None):
        return {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {}
            }
        }
    
    class ValidationError(Exception):
        pass
    
    class DatabaseError(Exception):
        pass
    
    class ServiceError(Exception):
        pass
    
    class AuthenticationError(Exception):
        pass
    
    # Mock database functions for fallback
    async def init_database(*args, **kwargs):
        return None
    
    async def query(*args, **kwargs):
        return []
    
    async def health_check():
        return True


# Re-export everything for easier imports
__all__ = [
    "logger",
    "validateRequired",
    "successResponse",
    "errorResponse",
    "ValidationError",
    "DatabaseError",
    "ServiceError",
    "AuthenticationError",
    "init_database",
    "query",
    "health_check",
]