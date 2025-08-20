"""
Security middleware and utilities for LiteLLM Gateway
Prompt injection detection and rate limiting
"""

import structlog
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .config import COMPILED_PATTERNS, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
from .models import SecurityAlert

logger = structlog.get_logger()

# Rate limiting storage
rate_limit_storage: Dict[str, List[datetime]] = {}

# Security alert storage
security_alerts: List[SecurityAlert] = []


class ErrorTracker:
    """Track and aggregate errors for monitoring"""
    
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.error_counts = {}
    
    def track_error(self, error_type: str, error_msg: str, context: Dict = None):
        """Track an error for monitoring purposes"""
        error_key = f"{error_type}:{error_msg[:100]}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        error_log_file = self.log_dir / f"errors_{datetime.utcnow().strftime('%Y%m%d')}.log"
        
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_msg,
            "count": self.error_counts[error_key],
            "context": context or {},
            "service": "litellm-gateway"
        }
        
        with open(error_log_file, "a") as f:
            f.write(f"{error_entry}\n")


error_tracker = ErrorTracker()


class SecurityMiddleware:
    """Security middleware for prompt injection detection and rate limiting"""
    
    @staticmethod
    def detect_prompt_injection(text: str) -> Optional[str]:
        """
        Detect potential prompt injection attempts
        Returns the matched pattern if injection detected, None otherwise
        """
        for pattern in COMPILED_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
        return None
    
    @staticmethod
    def check_rate_limit(client_id: str) -> bool:
        """
        Check if client is within rate limits
        Returns True if within limits, False otherwise
        """
        now = datetime.utcnow()
        
        if client_id in rate_limit_storage:
            rate_limit_storage[client_id] = [
                timestamp for timestamp in rate_limit_storage[client_id]
                if now - timestamp < RATE_LIMIT_WINDOW
            ]
        else:
            rate_limit_storage[client_id] = []
        
        current_count = len(rate_limit_storage[client_id])
        
        if current_count >= RATE_LIMIT_REQUESTS:
            return False
        
        rate_limit_storage[client_id].append(now)
        return True
    
    @staticmethod
    def log_security_alert(level: str, message: str, request_id: str):
        """Log security alert"""
        alert = SecurityAlert(
            level=level,
            message=message,
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        security_alerts.append(alert)
        
        if len(security_alerts) > 1000:
            security_alerts.pop(0)
        
        logger.warning(
            "security_alert",
            level=level,
            message=message,
            request_id=request_id
        )


def get_security_alerts() -> List[SecurityAlert]:
    """Get recent security alerts"""
    return security_alerts[-50:]


def get_security_config() -> Dict[str, any]:
    """Get current security configuration"""
    return {
        "injection_patterns_count": len(COMPILED_PATTERNS),
        "rate_limit_requests": RATE_LIMIT_REQUESTS,
        "rate_limit_window_minutes": RATE_LIMIT_WINDOW.total_seconds() / 60,
        "alert_count": len(security_alerts)
    }