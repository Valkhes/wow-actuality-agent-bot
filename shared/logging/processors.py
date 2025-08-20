"""
Log processors for structured logging
Context enrichment and formatting processors
"""

import os
import structlog
from typing import Any, Dict


def add_service_context(service_name: str, version: str = "1.0.0"):
    """Create service context processor"""
    def processor(logger, name, event_dict):
        event_dict["service"] = service_name
        event_dict["version"] = version
        event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
        event_dict["hostname"] = os.getenv("HOSTNAME", "unknown")
        return event_dict
    return processor


def add_error_tracking_processor(error_tracker):
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
        request_id = structlog.contextvars.get_context().get("request_id")
        if request_id:
            event_dict["request_id"] = request_id
        
        user_id = structlog.contextvars.get_context().get("user_id")
        if user_id:
            event_dict["user_id"] = user_id
        
        trace_id = structlog.contextvars.get_context().get("trace_id")
        if trace_id:
            event_dict["trace_id"] = trace_id
        
        return event_dict
    return processor


def add_performance_tracking_processor():
    """Add performance tracking processor"""
    def processor(logger, name, event_dict):
        if "duration" in event_dict:
            event_dict["performance"] = {
                "duration_ms": event_dict["duration"],
                "slow_query": event_dict["duration"] > 1000
            }
        
        if "memory_usage" in event_dict:
            event_dict["resource_usage"] = {
                "memory_mb": event_dict["memory_usage"],
                "high_memory": event_dict["memory_usage"] > 500
            }
        
        return event_dict
    return processor