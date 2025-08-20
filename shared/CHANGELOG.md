# Shared Utilities Changelog

All notable changes to the shared utilities will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-08-20

### Changed
- Refactored logging_utils.py into focused package for CLAUDE.md compliance
- Split 389-line logging_utils.py into 6 focused modules under 100 lines each
- Created logging package with clear separation of concerns:
  - config.py: Logging configuration (84 lines)
  - processors.py: Log processors and formatters (66 lines)
  - tracking.py: Error tracking functionality (87 lines)
  - middleware.py: Logging middleware classes (62 lines)
  - utils.py: Utility functions (40 lines)
  - __init__.py: Public API (18 lines)

## [1.0.0] - 2023-12-01

### Added
- Enhanced logging utilities for consistent structured logging
- Error tracking and aggregation across all services
- Performance monitoring with request/response timing
- Service context processors for log enrichment
- Request context management with trace IDs
- Comprehensive error tracking with alert thresholds
- LoggingMiddleware for automatic request/response logging
- Health metrics collection utilities
- JSON-formatted log output with structured data
- Configuration utilities for service setup

### Features
- Multi-service error tracking with centralized aggregation
- Performance metric collection and analysis
- Request tracing with correlation IDs
- Service health monitoring utilities
- Alert threshold management for critical errors
- Logging configuration with fallback support
- Cross-service logging consistency enforcement

### Infrastructure
- Python logging configuration with structlog
- Error tracking with file-based persistence
- Performance monitoring with timing utilities
- Service metadata injection for all log entries
- Environment-aware configuration management