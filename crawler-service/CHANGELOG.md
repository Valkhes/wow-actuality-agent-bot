# Crawler Service Changelog

All notable changes to the Crawler service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-08-21

### Changed
- Enhanced article chunking strategy with overlapping sliding window approach
- Improved content preservation with larger chunk sizes (1500 chars) and significant overlap (300 chars)
- Added comprehensive chunk metadata including position tracking and chunk indexing
- Optimized vector storage with better chunk organization for improved retrieval

### Fixed
- Resolved content loss issues in article chunking by ensuring complete coverage
- Improved word boundary detection to prevent mid-word cuts in chunks

## [1.0.1] - 2025-08-20

### Changed
- Replaced f-string logging with structured logging for better monitoring
- Updated link discovery logging to use structured format with counts and selectors

## [1.0.0] - 2023-12-01

### Added
- Web crawler for Blizzspirit.com article extraction
- Respectful crawling with configurable rate limiting (1 req/sec)
- HTML parsing optimized for Blizzspirit page structure
- Article metadata extraction (title, content, date, URL)
- Incremental crawling with file-based caching system
- Duplicate detection and content deduplication
- ChromaDB integration for vector storage
- Scheduled crawling with configurable intervals (default: 6 hours)
- Manual crawl trigger via API endpoint
- Clean architecture with domain/application/infrastructure layers
- Comprehensive error handling and retry logic
- Enhanced structured logging with crawl statistics
- Health check endpoints for monitoring
- Docker containerization with persistent cache volume

### Infrastructure
- BeautifulSoup4 for HTML parsing and content extraction
- Requests library with session management and retries
- File-based caching system for crawl state persistence
- Async scheduling system for automated crawls
- ChromaDB client integration with connection pooling
- Environment-based configuration
- Unit test coverage for parsing and storage logic

### Features
- Configurable maximum articles per crawl session
- Robust error recovery for network and parsing issues
- Crawl statistics and reporting via API endpoints
- Graceful shutdown handling with cleanup procedures