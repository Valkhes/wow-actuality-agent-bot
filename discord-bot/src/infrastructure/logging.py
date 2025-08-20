import structlog
import sys
import os
import logging
import traceback
from datetime import datetime
from pathlib import Path
from structlog.stdlib import LoggerFactory
from typing import Dict, Any, Optional


class ErrorTracker:
    """Track and aggregate errors for monitoring"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.error_counts = {}
    
    def track_error(self, error_type: str, error_msg: str, context: Dict[str, Any] = None):
        """Track an error for monitoring purposes"""
        error_key = f"{error_type}:{error_msg[:100]}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log to error tracking file
        error_log_file = self.log_dir / f"errors_{datetime.utcnow().strftime('%Y%m%d')}.log"
        
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_msg,
            "count": self.error_counts[error_key],
            "context": context or {},
            "service": "discord-bot"
        }
        
        with open(error_log_file, "a") as f:
            f.write(f"{error_entry}\n")


# Global error tracker instance
error_tracker = ErrorTracker()


def add_service_context(logger, name, event_dict):
    """Add service-specific context to all log entries"""
    event_dict["service"] = "discord-bot"
    event_dict["version"] = "1.0.0"
    event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
    return event_dict


def add_error_tracking(logger, name, event_dict):
    """Add error tracking for monitoring"""
    if event_dict.get("level") == "error":
        error_type = event_dict.get("error_type", "UnknownError")
        error_msg = event_dict.get("event", "Unknown error")
        context = {k: v for k, v in event_dict.items() 
                  if k not in ["event", "level", "timestamp", "logger"]}
        
        error_tracker.track_error(error_type, error_msg, context)
    
    return event_dict


def add_request_context(logger, name, event_dict):
    """Add request-specific context"""
    # Add request ID if available
    request_id = structlog.contextvars.get_context().get("request_id")
    if request_id:
        event_dict["request_id"] = request_id
    
    # Add user context if available
    user_id = structlog.contextvars.get_context().get("user_id")
    if user_id:
        event_dict["user_id"] = user_id
    
    return event_dict


def configure_logging(
    log_level: str = "INFO", 
    log_format: str = "json",
    log_dir: str = "./logs",
    enable_file_logging: bool = True
):
    """Configure enhanced structured logging with monitoring integration"""
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Base processors
    processors = [
        structlog.contextvars.merge_contextvars,
        add_service_context,
        add_request_context,
        add_error_tracking,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
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
        service_log_file = log_path / f"discord-bot_{datetime.utcnow().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(service_log_file)
        file_handler.setLevel(log_level_obj)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=log_level_obj,
    )
    
    # Set up discord.py logging
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)  # Discord.py can be very verbose
    
    # Set up other library logging
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Initialize structlog logger for startup
    logger = structlog.get_logger()
    logger.info(
        "Logging configured",
        log_level=log_level,
        log_format=log_format,
        log_dir=str(log_path),
        file_logging=enable_file_logging
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a logger instance with service context"""
    return structlog.get_logger(name)


def log_exception(logger: structlog.BoundLogger, exc: Exception, context: Dict[str, Any] = None):
    """Log an exception with full context"""
    logger.error(
        "Exception occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc(),
        context=context or {},
        exc_info=True
    )


def create_request_logger(request_id: str, user_id: Optional[str] = None) -> structlog.BoundLogger:
    """Create a logger with request context"""
    logger = structlog.get_logger()
    
    # Add context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)
    
    return logger


def get_error_stats() -> Dict[str, Any]:
    """Get error statistics for monitoring"""
    return {
        "error_counts": error_tracker.error_counts.copy(),
        "total_errors": sum(error_tracker.error_counts.values()),
        "unique_errors": len(error_tracker.error_counts),
        "service": "discord-bot",
        "timestamp": datetime.utcnow().isoformat()
    }