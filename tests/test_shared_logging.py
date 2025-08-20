"""
Unit tests for shared logging package
Tests for logging utilities, middleware, and error tracking
"""

import pytest
import json
import tempfile
import structlog
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pathlib import Path

from shared.logging import (
    configure_enhanced_logging,
    get_logger,
    log_exception,
    create_request_logger,
    LoggingMiddleware,
    log_performance_metric,
    ErrorTracker,
    get_service_health_metrics
)


class TestLoggingUtils:
    """Test logging utility functions"""
    
    def test_get_logger_returns_structured_logger(self):
        """Test logger creation returns structlog instance"""
        logger = get_logger("test-service")
        assert isinstance(logger, structlog.BoundLogger)
    
    def test_log_exception_captures_error_details(self):
        """Test exception logging includes all error context"""
        logger = Mock()
        test_exception = ValueError("Test error")
        context = {"user_id": "123", "action": "test"}
        
        log_exception(logger, test_exception, context, "CRITICAL")
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[0][0] == "Exception occurred"
        assert call_args[1]["error_type"] == "ValueError"
        assert call_args[1]["error_message"] == "Test error"
        assert call_args[1]["severity"] == "CRITICAL"
        assert call_args[1]["context"] == context
    
    def test_create_request_logger_binds_context(self):
        """Test request logger binds context variables"""
        with patch('structlog.contextvars.bind_contextvars') as mock_bind:
            logger = create_request_logger("req-123", "user-456", "trace-789")
            
            assert mock_bind.call_count == 3
            mock_bind.assert_any_call(request_id="req-123")
            mock_bind.assert_any_call(user_id="user-456")
            mock_bind.assert_any_call(trace_id="trace-789")


class TestLoggingMiddleware:
    """Test logging middleware functionality"""
    
    @pytest.mark.asyncio
    async def test_middleware_logs_request_response(self):
        """Test middleware logs request and response details"""
        middleware = LoggingMiddleware("test-service")
        
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "/api/test"
        mock_request.headers = {"user-agent": "test-client"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        
        async def mock_call_next(request):
            return mock_response
        
        with patch('shared.logging.middleware.create_request_logger') as mock_logger_creator:
            mock_logger = Mock()
            mock_logger_creator.return_value = mock_logger
            
            response = await middleware(mock_request, mock_call_next)
            
            assert response == mock_response
            assert mock_logger.info.call_count == 2  # Start and complete
    
    def test_log_performance_metric_formats_correctly(self):
        """Test performance metric logging format"""
        logger = Mock()
        metadata = {"query": "test", "rows": 10}
        
        log_performance_metric(logger, "db_query", 1500.5, True, metadata)
        
        logger.info.assert_called_once_with(
            "Performance metric",
            operation="db_query",
            duration=1500.5,
            success=True,
            slow_query=True,
            metadata=metadata
        )


class TestErrorTracker:
    """Test error tracking and aggregation"""
    
    def test_error_tracker_initialization(self):
        """Test error tracker setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = ErrorTracker("test-service", temp_dir)
            
            assert tracker.service_name == "test-service"
            assert tracker.log_dir == Path(temp_dir)
            assert len(tracker.error_counts) == 0
    
    def test_track_error_creates_log_entry(self):
        """Test error tracking creates proper log entry"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = ErrorTracker("test-service", temp_dir)
            context = {"user_id": "123"}
            
            tracker.track_error("ValueError", "Test error", context, "ERROR")
            
            # Check error count updated
            error_key = "ValueError:Test error"
            assert tracker.error_counts[error_key] == 1
            
            # Check log file created
            log_files = list(Path(temp_dir).glob("errors_*.json"))
            assert len(log_files) == 1
            
            # Check log entry content
            with open(log_files[0], 'r') as f:
                log_entry = json.loads(f.read().strip())
                assert log_entry["service"] == "test-service"
                assert log_entry["error_type"] == "ValueError"
                assert log_entry["context"] == context
    
    def test_get_service_health_metrics_format(self):
        """Test health metrics format and content"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = ErrorTracker("test-service", temp_dir)
            tracker.error_counts = {"Error1": 5, "Error2": 3}
            
            metrics = get_service_health_metrics(tracker)
            
            assert metrics["service"] == "test-service"
            assert metrics["total_errors"] == 8
            assert metrics["unique_errors"] == 2
            assert "timestamp" in metrics
            assert "error_counts" in metrics


class TestLoggingConfiguration:
    """Test logging configuration setup"""
    
    def test_configure_enhanced_logging_setup(self):
        """Test enhanced logging configuration"""
        with patch('structlog.configure') as mock_configure:
            configure_enhanced_logging("test-service", "DEBUG")
            
            mock_configure.assert_called_once()
            call_args = mock_configure.call_args[1]
            assert "processors" in call_args
            assert "logger_factory" in call_args