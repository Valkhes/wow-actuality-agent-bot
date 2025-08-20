"""
Logging middleware for request/response tracking
Performance monitoring and error handling
"""

import structlog
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from .utils import get_logger, log_exception, create_request_logger


class LoggingMiddleware:
    """Middleware for request/response logging"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"{service_name}.middleware")
    
    async def __call__(self, request, call_next):
        """Log request/response with timing"""
        start_time = datetime.utcnow()
        request_id = f"req_{start_time.timestamp()}"
        
        request_logger = create_request_logger(request_id)
        
        request_logger.info(
            "Request started",
            method=getattr(request, 'method', 'UNKNOWN'),
            path=getattr(request, 'url', str(request)),
            user_agent=getattr(request, 'headers', {}).get('user-agent', 'unknown')
        )
        
        try:
            response = await call_next(request)
            
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            request_logger.info(
                "Request completed",
                status_code=getattr(response, 'status_code', 'unknown'),
                duration=duration,
                success=True
            )
            
            return response
            
        except Exception as exc:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            log_exception(
                request_logger,
                exc,
                {"request_id": request_id, "duration": duration},
                "ERROR"
            )
            
            raise


def log_performance_metric(
    logger: structlog.BoundLogger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    metadata: Dict[str, Any] = None
):
    """Log performance metrics for monitoring"""
    logger.info(
        "Performance metric",
        operation=operation,
        duration=duration_ms,
        success=success,
        slow_query=duration_ms > 1000,
        metadata=metadata or {}
    )