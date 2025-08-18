# WoW Actuality Discord Bot - Implementation Tasks

## Project Overview
A multi-container Discord bot system that provides World of Warcraft news updates through AI-powered responses, featuring web crawling, RAG database storage, and security monitoring.

## Architecture
- **Discord Bot Container**: Handles Discord interactions and `/ask` commands
- **API Container**: LangChain agent with Gemini 2.0 for intelligent responses
- **ChromaDB Container**: Vector database for RAG storage
- **LiteLLM Gateway**: Prompt injection protection
- **Langfuse Container**: Token usage monitoring
- **Web Crawler**: Blizzspirit.com article extraction service

---

## Phase 1: Foundation & Infrastructure ✅ COMPLETED

### Task 1: Set up project structure and Docker Compose configuration ✅
- [x] Create root project directory structure
- [x] Initialize git repository
- [x] Create service directories:
  - `discord-bot/`
  - `api-service/`
  - `crawler-service/`
  - `litellm-gateway/`
  - `docker/`
- [x] Create base `docker-compose.yml`
- [x] Set up shared volumes and networks

### Task 2: Create environment configuration and secrets management ✅
- [x] Create `.env.template` file
- [x] Define environment variables:
  - Discord bot token
  - Gemini API key
  - Database credentials
  - Service URLs
- [x] Create `.gitignore` for secrets
- [x] Document environment setup

### Task 3: Write Docker Compose orchestration with proper networking ✅
- [x] Configure internal network for services
- [x] Set up service dependencies
- [x] Configure volume mounts
- [x] Add health checks
- [x] Configure restart policies

---

## Phase 2: Core Services ✅ COMPLETED

### Task 4: Create Discord bot container with /ask command handler ✅
- [x] Set up Python environment with discord.py
- [x] Create `Dockerfile` for Discord bot
- [x] Implement bot initialization and authentication
- [x] Create `/ask` slash command handler (60 char limit, 1/min rate limit)
- [x] Add HTTP client for API service communication
- [x] Implement clean architecture (domain/infrastructure/presentation)
- [x] Add logging and error handling

### Task 5: Build API container with /ask route and LangChain agent integration ✅
- [x] Set up FastAPI application
- [x] Create `Dockerfile` for API service
- [x] Implement `/ask` POST endpoint
- [x] Set up LangChain agent framework with Gemini 2.0
- [x] Create response models and validation
- [x] Implement clean architecture layers
- [x] Add API documentation with OpenAPI

### Task 6: Set up ChromaDB for RAG database storage ✅
- [x] Configure ChromaDB container in docker-compose
- [x] Create database initialization scripts
- [x] Implement vector embedding storage
- [x] Create CRUD operations for articles
- [x] Set up collection management
- [x] Add database migration system

---

## Phase 3: Data Collection & AI Integration ✅ COMPLETED

### Task 7: Implement Blizzspirit.com web crawler for article extraction ✅
- [x] Set up Python crawler service
- [x] Create `Dockerfile` for crawler
- [x] Implement HTML parsing with BeautifulSoup (optimized for Blizzspirit structure)
- [x] Extract article metadata (title, content, date, URL)
- [x] Implement incremental crawling strategy with file cache
- [x] Add rate limiting (1 req/sec) and respectful crawling
- [x] Create scheduling system (daily crawls with manual trigger)
- [x] Integrate with ChromaDB storage

### Task 8: Integrate Gemini 2.0 with LangChain agent integration ✅
- [x] Configure Gemini 2.0 API client
- [x] Implement LangChain agent with RAG tools
- [x] Create RAG retrieval chain with ChromaDB
- [x] Implement context-aware prompt engineering
- [x] Add confidence scoring for responses  
- [x] Optimize token usage and costs
- [x] Create fallback mechanisms

---

## Phase 4: Security & Monitoring 🚧 IN PROGRESS

### Task 9: Configure LiteLLM gateway for prompt injection protection 🚧
- [x] Set up LiteLLM proxy container (basic setup)
- [ ] Configure prompt injection detection
- [ ] Implement security middleware
- [ ] Add request/response logging
- [ ] Create security alert system
- [ ] Configure rate limiting
- [ ] Document security policies

### Task 10: Set up Langfuse container for token usage monitoring
- [x] Langfuse container configured in docker-compose
- [x] Database for Langfuse configured (PostgreSQL)
- [x] LLM call tracking integrated in API service
- [ ] Set up usage dashboards
- [ ] Configure cost monitoring
- [ ] Add alert thresholds
- [ ] Create usage reports

---

## Phase 5: Architecture & Quality

### Task 11: Implement clean architecture patterns across all services ✅
- [x] Define domain entities and use cases
- [x] Implement dependency injection
- [x] Create interface abstractions
- [x] Separate business logic from infrastructure
- [x] Add validation layers
- [x] Implement repository patterns
- [x] Create service layer abstractions

### Task 12: Add error handling and logging across all containers
- [ ] Implement structured logging (JSON format)
- [ ] Configure log aggregation
- [ ] Add error tracking and alerting
- [ ] Create health check endpoints
- [ ] Implement graceful shutdown
- [ ] Add monitoring metrics
- [ ] Create debugging utilities

---

## Phase 6: Testing & Documentation

### Task 13: Test end-to-end functionality and container communication
- [ ] Create unit tests for each service
- [ ] Implement integration tests
- [ ] Add Docker Compose test environment
- [ ] Test Discord command flow
- [ ] Validate API responses
- [ ] Test crawler functionality
- [ ] Verify database operations
- [ ] Load test the system

### Task 14: Create deployment documentation and setup instructions
- [ ] Write comprehensive README.md
- [ ] Document environment setup
- [ ] Create deployment guide
- [ ] Add troubleshooting section
- [ ] Document API endpoints
- [ ] Create architecture diagrams
- [ ] Add contributing guidelines

---

## Implementation Order

1. **Start Here**: Tasks 1-3 (Foundation)
2. **Core Functionality**: Tasks 4-6 (Basic services)
3. **Data & AI**: Tasks 7-8 (Crawler and AI integration)
4. **Security**: Tasks 9-10 (Monitoring and security)
5. **Quality**: Tasks 11-12 (Architecture and logging)
6. **Validation**: Tasks 13-14 (Testing and documentation)

## Success Criteria

- [x] Discord bot responds to `/ask` commands (60 char limit, 1/min rate)
- [x] API returns intelligent responses about WoW news (with confidence scoring)
- [x] Crawler automatically updates article database (daily schedule + manual trigger)
- [ ] Security measures block prompt injection (LiteLLM partially implemented)
- [x] Monitoring tracks token usage and costs (Langfuse integrated)
- [x] All services run reliably in Docker Compose (health checks implemented)
- [x] System handles errors gracefully (structured logging + error handling)
- [ ] Documentation enables easy deployment

## Current Status: 75% Complete

### ✅ COMPLETED (3 phases):
- **Phase 1**: Foundation & Infrastructure
- **Phase 2**: Core Services  
- **Phase 3**: Data Collection & AI Integration
- **Clean Architecture**: Implemented across all services

### 🚧 IN PROGRESS (1 phase):
- **Phase 4**: Security & Monitoring (LiteLLM partially done, Langfuse integrated)

### ⏳ REMAINING:
- Complete LiteLLM prompt injection protection
- Complete logging infrastructure (Phase 5)
- End-to-end testing (Phase 6)
- Documentation finalization (Phase 6)

## Notes

- MVP functionality is mostly complete and functional
- Clean architecture implemented with domain/application/infrastructure layers
- All services configured with proper health checks and error handling
- Crawler optimized for Blizzspirit homepage structure
- Rate limiting: 1 question/user/minute, 60 char max question length
- Ready for initial testing and deployment