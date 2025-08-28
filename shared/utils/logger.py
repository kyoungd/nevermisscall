"""
Logging utilities for NeverMissCall shared library.

Provides structured logging with timestamps following the
logging patterns defined in shared.md documentation.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import json


class CustomFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging.
    
    Formats log messages as JSON with consistent structure
    for better log aggregation and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data, default=str)


class NeverMissCallLogger:
    """
    Custom logger class for NeverMissCall services.
    
    Provides structured logging with consistent format and
    extra context support for better debugging.
    """
    
    def __init__(self, name: str = 'nevermisscall'):
        """
        Initialize logger with name.
        
        Args:
            name: Logger name (usually service name)
        """
        self._logger = logging.getLogger(name)
        
        # Set up handler if not already configured
        if not self._logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Set up logger with custom formatter and handler."""
        # Set level from environment or default to INFO
        import os
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self._logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CustomFormatter())
        
        self._logger.addHandler(handler)
        
        # Prevent propagation to avoid duplicate logs
        self._logger.propagate = False
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log info level message.
        
        Args:
            message: Log message
            extra: Optional extra data dictionary
        """
        self._log(logging.INFO, message, extra)
    
    def error(self, message: str, error: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error level message.
        
        Args:
            message: Log message
            error: Optional exception object
            extra: Optional extra data dictionary
        """
        log_extra = extra or {}
        
        if error:
            log_extra['error_type'] = type(error).__name__
            log_extra['error_message'] = str(error)
        
        self._log(logging.ERROR, message, log_extra, exc_info=error is not None)
    
    def warn(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log warning level message.
        
        Args:
            message: Log message
            extra: Optional extra data dictionary
        """
        self._log(logging.WARNING, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Alias for warn method."""
        self.warn(message, extra)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log debug level message (only in development).
        
        Args:
            message: Log message
            extra: Optional extra data dictionary
        """
        self._log(logging.DEBUG, message, extra)
    
    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> None:
        """
        Internal logging method.
        
        Args:
            level: Log level
            message: Log message
            extra: Optional extra data
            exc_info: Whether to include exception info
        """
        # Create log record with extra data
        record = self._logger.makeRecord(
            name=self._logger.name,
            level=level,
            fn='',
            lno=0,
            msg=message,
            args=(),
            exc_info=sys.exc_info() if exc_info else None
        )
        
        # Add extra data to record
        if extra:
            record.extra_data = extra
        
        # Handle the record
        self._logger.handle(record)
    
    def set_context(self, **kwargs) -> 'LoggerContext':
        """
        Create a logger context with additional fields.
        
        Args:
            **kwargs: Context fields to add to all log messages
            
        Returns:
            LoggerContext object
        """
        return LoggerContext(self, kwargs)


class LoggerContext:
    """
    Logger context manager for adding consistent fields to log messages.
    
    Useful for adding request IDs, user IDs, tenant IDs, etc. to all
    log messages within a specific context.
    """
    
    def __init__(self, logger: NeverMissCallLogger, context: Dict[str, Any]):
        """
        Initialize logger context.
        
        Args:
            logger: Logger instance
            context: Context fields to add
        """
        self._logger = logger
        self._context = context
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info with context."""
        self._logger.info(message, {**self._context, **(extra or {})})
    
    def error(self, message: str, error: Optional[Exception] = None, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error with context."""
        self._logger.error(message, error, {**self._context, **(extra or {})})
    
    def warn(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning with context."""
        self._logger.warn(message, {**self._context, **(extra or {})})
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug with context."""
        self._logger.debug(message, {**self._context, **(extra or {})})


# Create default logger instance
logger = NeverMissCallLogger()


# Convenience functions for common logging patterns
def log_api_request(method: str, path: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> None:
    """
    Log API request with standard fields.
    
    Args:
        method: HTTP method
        path: Request path
        user_id: User ID (optional)
        tenant_id: Tenant ID (optional)
    """
    extra = {
        'event_type': 'api_request',
        'method': method,
        'path': path
    }
    
    if user_id:
        extra['user_id'] = user_id
    if tenant_id:
        extra['tenant_id'] = tenant_id
    
    logger.info(f"{method} {path}", extra=extra)


def log_api_response(method: str, path: str, status_code: int, duration_ms: int, user_id: Optional[str] = None, tenant_id: Optional[str] = None) -> None:
    """
    Log API response with standard fields.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: User ID (optional)
        tenant_id: Tenant ID (optional)
    """
    extra = {
        'event_type': 'api_response',
        'method': method,
        'path': path,
        'status_code': status_code,
        'duration_ms': duration_ms
    }
    
    if user_id:
        extra['user_id'] = user_id
    if tenant_id:
        extra['tenant_id'] = tenant_id
    
    level = 'error' if status_code >= 500 else 'warn' if status_code >= 400 else 'info'
    getattr(logger, level)(f"{method} {path} {status_code} ({duration_ms}ms)", extra=extra)


def log_database_operation(operation: str, table: str, duration_ms: int, record_count: Optional[int] = None) -> None:
    """
    Log database operation with performance metrics.
    
    Args:
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration_ms: Operation duration in milliseconds
        record_count: Number of records affected (optional)
    """
    extra = {
        'event_type': 'database_operation',
        'operation': operation,
        'table': table,
        'duration_ms': duration_ms
    }
    
    if record_count is not None:
        extra['record_count'] = record_count
    
    message = f"Database {operation} on {table} ({duration_ms}ms)"
    if record_count is not None:
        message += f" - {record_count} records"
    
    logger.debug(message, extra=extra)


def log_external_service_call(service: str, operation: str, status_code: int, duration_ms: int) -> None:
    """
    Log external service call with performance metrics.
    
    Args:
        service: Service name (twilio, openai, etc.)
        operation: Operation performed
        status_code: Response status code
        duration_ms: Call duration in milliseconds
    """
    extra = {
        'event_type': 'external_service_call',
        'service': service,
        'operation': operation,
        'status_code': status_code,
        'duration_ms': duration_ms
    }
    
    level = 'error' if status_code >= 500 else 'warn' if status_code >= 400 else 'info'
    message = f"{service.title()} {operation} {status_code} ({duration_ms}ms)"
    
    getattr(logger, level)(message, extra=extra)