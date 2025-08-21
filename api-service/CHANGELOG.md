# API Service Changelog

All notable changes to the API service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-08-20

### Changed
- Enhanced ChromaDB repository with improved query processing and multi-query search
- Added enhanced query functionality with French stop-word filtering for better retrieval
- Improved context formatting in LiteLLM repository with longer content previews (1000 chars)
- Updated similarity score threshold for source articles to capture more relevant results
- Added comprehensive debugging and logging throughout AI repositories
- Enhanced confidence calculation algorithms for better response quality assessment

### Fixed
- Improved vector document search with deduplication and better scoring
- Enhanced error handling and fallback responses in AI repositories

## [1.0.0] - 2023-12-01

### Added
- FastAPI-based REST API with OpenAPI documentation
- `/ask` endpoint for AI-powered Q&A processing
- LangChain integration with Gemini 2.0 Flash model
- RAG (Retrieval-Augmented Generation) with ChromaDB
- LiteLLM gateway integration for secure LLM access
- Prompt injection protection and security filtering
- Confidence scoring for AI responses
- Source article attribution and citation
- Clean architecture with domain/application/infrastructure layers
- Comprehensive error handling and fallback mechanisms
- Enhanced structured logging with performance tracking
- Health check endpoints with dependency validation
- Monitoring endpoints for metrics and usage statistics
- Langfuse integration for observability and cost tracking
- Docker containerization with multi-stage builds

### Infrastructure
- ChromaDB vector database integration
- PostgreSQL database support via Langfuse
- Environment-based configuration management
- Async/await patterns throughout the codebase
- Type hints and Pydantic models for data validation
- Unit and integration test coverage
- Performance monitoring and slow query detection

### Security
- Input validation and sanitization
- Rate limiting integration
- Secure API key management
- Request/response logging for audit trails