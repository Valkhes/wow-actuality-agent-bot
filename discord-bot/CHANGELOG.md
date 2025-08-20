# Discord Bot Service Changelog

All notable changes to the Discord Bot service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-08-20

### Changed
- Removed emojis from error messages and user-facing text for CLAUDE.md compliance
- Replaced emoji-based status indicators with plain text equivalents
- Replaced f-string logging with structured logging for better monitoring
- Updated command sync logging to use structured format with command count

## [1.0.0] - 2023-12-01

### Added
- Initial Discord bot implementation with slash commands
- `/ask` command for World of Warcraft Q&A
- Rate limiting (1 request per user per minute)
- Question length validation (configurable max length)
- Clean architecture with domain/application/infrastructure layers
- HTTP client integration with API service
- Comprehensive error handling and fallback responses
- Enhanced structured logging with error tracking
- Health check endpoints for monitoring
- Docker containerization with health checks
- Environment-based configuration
- Unit test coverage for core functionality

### Infrastructure
- Docker container setup with Python 3.11
- Discord.py integration for bot functionality
- Structured logging with JSON output
- Rate limiting with in-memory storage
- HTTP client with timeout and retry logic
- Clean shutdown handling