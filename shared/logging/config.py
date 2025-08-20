"""
Logging configuration for WoW Actuality Bot services
Enhanced structured logging setup with monitoring integration
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from structlog.stdlib import LoggerFactory
import structlog

from .processors import (
    add_service_context,
    add_error_tracking_processor,
    add_request_context_processor,
    add_performance_tracking_processor
)
from .tracking import ErrorTracker


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
    
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    error_tracker = None
    if enable_error_tracking:
        error_tracker = ErrorTracker(service_name, log_dir)
    
    processors = [
        structlog.contextvars.merge_contextvars,
        add_service_context(service_name, version),
        add_request_context_processor(),
    ]
    
    if enable_error_tracking and error_tracker:
        processors.append(add_error_tracking_processor(error_tracker))
    
    if enable_performance_tracking:
        processors.append(add_performance_tracking_processor())
    
    processors.extend([
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ])
    
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
    
    log_level_obj = getattr(logging, log_level.upper(), logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_obj)
    
    handlers = [console_handler]
    
    if enable_file_logging:
        service_log_file = log_path / f"{service_name}_{datetime.utcnow().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(service_log_file)
        file_handler.setLevel(log_level_obj)
        handlers.append(file_handler)
    
    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=log_level_obj,
    )
    
    _suppress_noisy_loggers()
    
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


def _suppress_noisy_loggers():
    """Suppress noisy third-party loggers"""
    noisy_loggers = [
        'discord', 'aiohttp', 'urllib3', 'chromadb', 'httpx',
        'langchain', 'google', 'openai', 'anthropic'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)