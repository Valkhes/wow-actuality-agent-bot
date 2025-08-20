"""
Shared logging utilities for WoW Actuality Bot services
Enhanced structured logging with monitoring integration
"""

import structlog
import sys
import os
import logging
import traceback
import json
from datetime import datetime
from pathlib import Path
from structlog.stdlib import LoggerFactory
from typing import Dict, Any, Optional, List


class ErrorTracker:
    """Track and aggregate errors for monitoring across services"""
    
    def __init__(self, service_name: str, log_dir: str = "./logs"):
        self.service_name = service_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.error_counts = {}
        self.alert_thresholds = {
            "error_rate_5min": 10,
            "critical_error_count": 5,
            "timeout_count": 3
        }
    
    def track_error(self, error_type: str, error_msg: str, context: Dict[str, Any] = None, severity: str = "ERROR"):
        """Track an error for monitoring purposes"""
        error_key = f"{error_type}:{error_msg[:100]}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log to error tracking file
        error_log_file = self.log_dir / f"errors_{datetime.utcnow().strftime('%Y%m%d')}.json"
        
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "error_type": error_type,
            "error_message": error_msg,
            "severity": severity,
            "count": self.error_counts[error_key],
            "context": context or {}
        }
        
        # Append to daily error log
        with open(error_log_file, "a") as f:
            f.write(json.dumps(error_entry) + "\n")
        
        # Check alert thresholds
        self._check_alert_thresholds(error_type, severity)
    
    def _check_alert_thresholds(self, error_type: str, severity: str):
        """Check if error patterns trigger alerts"""
        if severity == "CRITICAL":
            critical_count = sum(1 for k in self.error_counts.keys() 
                               if "CRITICAL" in k or "TimeoutError" in k or "ConnectionError" in k)
            if critical_count >= self.alert_thresholds["critical_error_count"]:
                self._trigger_alert("CRITICAL", f"Critical error threshold exceeded: {critical_count} errors")
    
    def _trigger_alert(self, level: str, message: str):
        """Trigger monitoring alert (placeholder for real alerting system)"""
        alert_file = self.log_dir / "alerts.json"
        
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "level": level,
            "message": message,
            "alert_id": f"alert_{datetime.utcnow().timestamp()}"
        }
        
        with open(alert_file, "a") as f:
            f.write(json.dumps(alert) + "\n")


def add_service_context(service_name: str, version: str = "1.0.0"):
    """Create service context processor"""
    def processor(logger, name, event_dict):
        event_dict["service"] = service_name
        event_dict["version"] = version
        event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
        event_dict["hostname"] = os.getenv("HOSTNAME", "unknown")
        return event_dict
    return processor


def add_error_tracking_processor(error_tracker: ErrorTracker):
    """Create error tracking processor"""
    def processor(logger, name, event_dict):
        level = event_dict.get("level", "").upper()
        if level in ["ERROR", "CRITICAL"]:
            error_type = event_dict.get("error_type", type(event_dict.get("exception", Exception())).__name__)
            error_msg = event_dict.get("event", str(event_dict.get("exception", "Unknown error")))
            context = {k: v for k, v in event_dict.items() 
                      if k not in ["event", "level", "timestamp", "logger", "exception"]}
            
            error_tracker.track_error(error_type, error_msg, context, level)
        
        return event_dict
    return processor


def add_request_context_processor():
    """Add request-specific context processor"""
    def processor(logger, name, event_dict):
        # Add request ID if available
        request_id = structlog.contextvars.get_context().get("request_id")
        if request_id:
            event_dict["request_id"] = request_id
        
        # Add user context if available
        user_id = structlog.contextvars.get_context().get("user_id")
        if user_id:
            event_dict["user_id"] = user_id
        
        # Add trace context if available
        trace_id = structlog.contextvars.get_context().get("trace_id")
        if trace_id:
            event_dict["trace_id"] = trace_id
        
        return event_dict
    return processor


def add_performance_tracking_processor():
    """Add performance tracking processor"""
    def processor(logger, name, event_dict):
        # Track response times
        if "duration" in event_dict:
            event_dict["performance"] = {
                "duration_ms": event_dict["duration"],
                "slow_query": event_dict["duration"] > 1000  # Mark as slow if > 1 second
            }
        
        # Track resource usage if available
        if "memory_usage" in event_dict:
            event_dict["resource_usage"] = {
                "memory_mb": event_dict["memory_usage"],
                "high_memory": event_dict["memory_usage"] > 500  # Mark as high if > 500MB
            }
        
        return event_dict
    return processor


def configure_enhanced_logging(
    service_name: str,
    version: str = "1.0.0",
    log_level: str = "INFO", 
    log_format: str = "json",
    log_dir: str = "./logs",
    enable_file_logging: bool = True,
    enable_error_tracking: bool = True,
    enable_performance_tracking: bool = True
) -> ErrorTracker:
    """Configure enhanced structured logging for a service"""
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create error tracker
    error_tracker = None
    if enable_error_tracking:
        error_tracker = ErrorTracker(service_name, log_dir)
    
    # Base processors
    processors = [
        structlog.contextvars.merge_contextvars,
        add_service_context(service_name, version),
        add_request_context_processor(),
    ]
    
    # Add optional processors
    if enable_error_tracking and error_tracker:
        processors.append(add_error_tracking_processor(error_tracker))
    
    if enable_performance_tracking:
        processors.append(add_performance_tracking_processor())
    
    # Core processors
    processors.extend([
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ])
    
    # Output processors
    if log_format.lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    log_level_obj = getattr(logging, log_level.upper(), logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_obj)
    
    handlers = [console_handler]
    
    # File handler (if enabled)
    if enable_file_logging:
        service_log_file = log_path / f"{service_name}_{datetime.utcnow().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(service_log_file)
        file_handler.setLevel(log_level_obj)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=log_level_obj,
    )
    
    # Suppress noisy third-party loggers
    noisy_loggers = [
        'discord', 'aiohttp', 'urllib3', 'chromadb', 'httpx',
        'langchain', 'google', 'openai', 'anthropic'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Initialize structlog logger for startup
    logger = structlog.get_logger()
    logger.info(
        "Enhanced logging configured",
        service=service_name,
        version=version,
        log_level=log_level,
        log_format=log_format,
        log_dir=str(log_path),
        file_logging=enable_file_logging,
        error_tracking=enable_error_tracking,
        performance_tracking=enable_performance_tracking
    )
    
    return error_tracker


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
    
    # Clear and set context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)
    
    if trace_id:
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
    
    return logger


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


def get_service_health_metrics(error_tracker: ErrorTracker = None) -> Dict[str, Any]:
    """Get service health metrics for monitoring"""
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": "TODO: implement uptime tracking",
        "memory_usage_mb": "TODO: implement memory tracking",
        "active_connections": "TODO: implement connection tracking"
    }
    
    if error_tracker:
        metrics.update({
            "error_counts": error_tracker.error_counts.copy(),
            "total_errors": sum(error_tracker.error_counts.values()),
            "unique_errors": len(error_tracker.error_counts),
            "service": error_tracker.service_name
        })
    
    return metrics


class LoggingMiddleware:
    """Middleware for request/response logging"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(f"{service_name}.middleware")
    
    async def __call__(self, request, call_next):
        """Log request/response with timing"""
        start_time = datetime.utcnow()
        request_id = f"req_{start_time.timestamp()}"
        
        # Create request logger
        request_logger = create_request_logger(request_id)
        
        request_logger.info(
            "Request started",
            method=getattr(request, 'method', 'UNKNOWN'),
            path=getattr(request, 'url', str(request)),
            user_agent=getattr(request, 'headers', {}).get('user-agent', 'unknown')
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
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