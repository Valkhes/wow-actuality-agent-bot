"""
Enhanced logging configuration for API service
Uses shared logging utilities for consistency across services
"""

import sys
import os
from pathlib import Path

# Add shared utilities to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))

try:
    from logging_utils import (
        configure_enhanced_logging,
        get_logger,
        log_exception,
        create_request_logger,
        log_performance_metric,
        get_service_health_metrics,
        LoggingMiddleware
    )
    ENHANCED_LOGGING_AVAILABLE = True
except ImportError:
    # Fallback to basic logging if shared utilities not available
    import structlog
    import logging
    from structlog.stdlib import LoggerFactory
    ENHANCED_LOGGING_AVAILABLE = False


def configure_logging(
    log_level: str = "INFO", 
    log_format: str = "json",
    log_dir: str = "./logs"
):
    """Configure logging for API service"""
    
    if ENHANCED_LOGGING_AVAILABLE:
        # Use enhanced logging
        error_tracker = configure_enhanced_logging(
            service_name="api-service",
            version="1.0.0",
            log_level=log_level,
            log_format=log_format,
            log_dir=log_dir,
            enable_file_logging=True,
            enable_error_tracking=True,
            enable_performance_tracking=True
        )
        return error_tracker
    else:
        # Fallback to basic logging
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
        ]
        
        if log_format.lower() == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.extend([
                structlog.dev.ConsoleRenderer(colors=True),
            ])
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, log_level.upper(), logging.INFO),
        )
        
        return None


# Export enhanced logging functions if available, otherwise provide fallbacks
if ENHANCED_LOGGING_AVAILABLE:
    __all__ = [
        'configure_logging',
        'get_logger', 
        'log_exception',
        'create_request_logger',
        'log_performance_metric',
        'get_service_health_metrics',
        'LoggingMiddleware'
    ]
else:
    # Fallback implementations
    def get_logger(name: str = None):
        return structlog.get_logger(name)
    
    def log_exception(logger, exc, context=None, severity="ERROR"):
        logger.error(
            "Exception occurred",
            error=str(exc),
            error_type=type(exc).__name__,
            context=context or {},
            exc_info=True
        )
    
    def create_request_logger(request_id: str, user_id=None, trace_id=None):
        return structlog.get_logger()
    
    def log_performance_metric(logger, operation: str, duration_ms: float, success=True, metadata=None):
        logger.info(
            "Performance metric",
            operation=operation,
            duration=duration_ms,
            success=success,
            metadata=metadata or {}
        )
    
    def get_service_health_metrics(error_tracker=None):
        return {
            "service": "api-service",
            "timestamp": "unknown",
            "enhanced_logging": False
        }
    
    class LoggingMiddleware:
        def __init__(self, service_name: str):
            self.service_name = service_name
        
        async def __call__(self, request, call_next):
            return await call_next(request)
    
    __all__ = [
        'configure_logging',
        'get_logger', 
        'log_exception',
        'create_request_logger',
        'log_performance_metric',
        'get_service_health_metrics',
        'LoggingMiddleware'
    ]