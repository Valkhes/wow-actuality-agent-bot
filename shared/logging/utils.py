"""
Utility functions for enhanced logging
Logger creation and exception handling
"""

import structlog
import traceback
from typing import Dict, Any, Optional


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a logger instance with service context"""
    return structlog.get_logger(name)


def log_exception(
    logger: structlog.BoundLogger, 
    exc: Exception, 
    context: Dict[str, Any] = None,
    severity: str = "ERROR"
):
    """Log an exception with full context and tracking"""
    logger.error(
        "Exception occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        severity=severity,
        traceback=traceback.format_exc(),
        context=context or {},
        exception=exc,
        exc_info=True
    )


def create_request_logger(
    request_id: str, 
    user_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> structlog.BoundLogger:
    """Create a logger with request context"""
    logger = structlog.get_logger()
    
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)
    
    if trace_id:
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
    
    return logger