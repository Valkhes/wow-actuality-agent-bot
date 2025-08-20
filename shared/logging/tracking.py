"""
Error tracking and aggregation for monitoring
Performance and health metrics collection
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


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
        
        with open(error_log_file, "a") as f:
            f.write(json.dumps(error_entry) + "\n")
        
        self._check_alert_thresholds(error_type, severity)
    
    def _check_alert_thresholds(self, error_type: str, severity: str):
        """Check if error patterns trigger alerts"""
        if severity == "CRITICAL":
            critical_count = sum(1 for k in self.error_counts.keys() 
                               if "CRITICAL" in k or "TimeoutError" in k or "ConnectionError" in k)
            if critical_count >= self.alert_thresholds["critical_error_count"]:
                self._trigger_alert("CRITICAL", f"Critical error threshold exceeded: {critical_count} errors")
    
    def _trigger_alert(self, level: str, message: str):
        """Trigger monitoring alert"""
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