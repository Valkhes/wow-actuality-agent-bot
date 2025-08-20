# WoW Actuality Discord Bot

A sophisticated Discord bot that provides AI-powered World of Warcraft news and updates through a multi-container architecture featuring web scraping, vector databases, intelligent responses, and comprehensive security monitoring.

## 🏗️ Architecture Overview

The bot consists of multiple containerized services working together:

- **Discord Bot**: Handles Discord interactions and `/ask` commands with rate limiting
- **API Service**: LangChain-powered AI agent with Gemini integration and RAG
- **LiteLLM Gateway**: Secure LLM proxy with prompt injection protection
- **ChromaDB**: Vector database for RAG (Retrieval-Augmented Generation)
- **Web Crawler**: Automated scraper for Blizzspirit.com articles with respectful crawling
- **PostgreSQL**: Database backend for monitoring and user data
- **Langfuse**: Comprehensive monitoring, usage tracking, and cost analysis
- **Enhanced Logging**: Structured logging with error tracking and performance monitoring

## ✨ Key Features

### Core Functionality
- **Intelligent Q&A**: Ask questions about WoW and get AI-powered responses based on the latest news
- **Automatic Content Updates**: Continuous scraping of WoW news sources with intelligent deduplication
- **Rate Limiting**: 1 question per user per minute with configurable character limits
- **Clean Architecture**: Domain-driven design with dependency injection across all services

### Security & Monitoring
- **Prompt Injection Protection**: LiteLLM gateway with pattern-based security filtering
- **Comprehensive Monitoring**: Usage tracking, error monitoring, and performance metrics
- **Structured Logging**: JSON-formatted logs with error aggregation and alerting
- **Security Event Tracking**: Real-time monitoring of security threats and blocked requests
- **Cost Monitoring**: Track LLM token usage and API costs with configurable alerts

### Performance & Reliability
- **Scalable Deployment**: Docker Compose orchestration with health checks
- **Graceful Error Handling**: Comprehensive error recovery and fallback mechanisms
- **Performance Optimization**: Response caching, connection pooling, and efficient vector searches
- **End-to-End Testing**: Comprehensive test suite with integration and load testing

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose (v3.8+)
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Environment Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd wow-actuality-agent-bot
```

2. **Create environment file:**
```bash
cp .env.template .env
# Edit .env with your API keys (see configuration section below)
```

3. **Start the services:**
```bash
docker-compose up -d
```

4. **Verify deployment:**
```bash
# Check all services are healthy
./scripts/health_monitor.sh -a

# View logs
docker-compose logs -f
```

5. **Invite bot to Discord:**
   - Go to Discord Developer Portal
   - Select your application → OAuth2 → URL Generator
   - Select "bot" and "applications.commands" scopes
   - Select "Send Messages" and "Use Slash Commands" permissions
   - Use generated URL to invite bot to your server

### Required Environment Variables

```env
# Discord Configuration
DISCORD_BOT_TOKEN=your_discord_bot_token

# AI Configuration  
GOOGLE_API_KEY=your_google_gemini_api_key

# Security Configuration
LITELLM_MASTER_KEY=your_secure_master_key_here

# Monitoring Configuration
LANGFUSE_SECRET_KEY=your_langfuse_secret
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key

# Database Configuration
POSTGRES_USER=wowbot
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=wowactuality

# Service Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
LITELLM_GATEWAY_URL=http://litellm-gateway:4000
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
```

## 🎮 Usage

Once deployed, invite the bot to your Discord server and use the `/ask` command:

```
/ask question: What are the latest WoW expansion features?
```

**The bot will:**
1. Validate and rate-limit your request
2. Check for prompt injection attempts via LiteLLM gateway
3. Query the vector database for relevant context from crawled articles
4. Generate an AI-powered response using Gemini 2.0
5. Return the answer with source citations and confidence score
6. Log the interaction for monitoring and cost tracking

**Response Format:**
```
Here are the latest World of Warcraft expansion features based on recent news:

[AI-generated response with latest information]

Sources:
1. https://blizzspirit.com/article-1
2. https://blizzspirit.com/article-2

Confidence: 92%
```

## 📊 Monitoring & Analytics

### Langfuse Dashboard
Access comprehensive analytics at `http://localhost:3000`:
- **Usage Metrics**: Question volume, response times, user engagement
- **Cost Analysis**: Token usage, API costs, and budget tracking
- **Performance Analytics**: Slow queries, error rates, and optimization insights
- **User Behavior**: Most asked questions, user patterns, and satisfaction metrics

### Security Monitoring
- **Real-time Alerts**: Prompt injection attempts and security violations
- **Rate Limit Tracking**: User behavior and potential abuse patterns
- **Error Analysis**: Failed requests, timeouts, and system issues

### System Health
```bash
# Check service health
./scripts/health_monitor.sh

# Generate log analysis report
./scripts/log_aggregator.py --date $(date +%Y%m%d)

# Setup monitoring dashboards
./scripts/setup_monitoring.py
```

## 🔧 Configuration

### Service Configuration

#### Discord Bot
```env
DISCORD_BOT_TOKEN=your_bot_token
API_SERVICE_URL=http://api-service:8000
RATE_LIMIT_REQUESTS_PER_MINUTE=60
MAX_QUESTION_LENGTH=500
LOG_LEVEL=INFO
```

#### API Service
```env
GOOGLE_API_KEY=your_gemini_api_key
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
LITELLM_GATEWAY_URL=http://litellm-gateway:4000
AI_MODEL_NAME=gemini-2.0-flash-exp
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000
MAX_CONTEXT_DOCUMENTS=5
```

#### LiteLLM Gateway
```env
LITELLM_MASTER_KEY=secure_master_key
GOOGLE_API_KEY=your_gemini_api_key
LOG_LEVEL=INFO
```

#### Crawler Service
```env
CHROMADB_HOST=chromadb
BLIZZSPIRIT_BASE_URL=https://www.blizzspirit.com
CRAWLER_INTERVAL_HOURS=6
CRAWLER_MAX_ARTICLES=100
```

### Database Configuration

```yaml
# ChromaDB for vector storage
chromadb:
  host: chromadb
  port: 8000
  collection: wow_articles
  
# PostgreSQL for structured data
postgres:
  host: postgres
  port: 5432
  database: wowactuality
  user: wowbot
```

## 📡 API Endpoints

### API Service (`http://localhost:8000`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/ask` | POST | Submit question to AI |
| `/monitoring/metrics` | GET | System metrics |
| `/monitoring/usage` | GET | Usage statistics |
| `/docs` | GET | API documentation |

#### `/ask` Request Format
```json
{
  "question": "What are the latest WoW updates?",
  "user_id": "12345",
  "username": "DiscordUser"
}
```

#### `/ask` Response Format
```json
{
  "response": "Here are the latest World of Warcraft updates...",
  "source_articles": [
    "https://blizzspirit.com/article1",
    "https://blizzspirit.com/article2"
  ],
  "confidence": 0.92,
  "timestamp": "2023-12-01T12:00:00Z"
}
```

### LiteLLM Gateway (`http://localhost:4000`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Gateway health check |
| `/chat/completions` | POST | Secure LLM completions |
| `/security/alerts` | GET | Recent security alerts |
| `/security/config` | GET | Security configuration |
| `/models` | GET | Available models |

### Crawler Service (`http://localhost:8002`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Crawler health check |
| `/crawl/manual` | POST | Trigger manual crawl |
| `/stats` | GET | Crawl statistics |

### Langfuse Dashboard (`http://localhost:3000`)

- **Home**: Overview and recent activity
- **Traces**: Detailed request traces and performance
- **Generations**: LLM generation analytics
- **Users**: User behavior and patterns
- **Settings**: Configuration and API keys

## 🧪 Testing

### Running Tests

```bash
# Unit tests
./scripts/run_tests.sh unit

# Integration tests (requires running services)
./scripts/run_tests.sh integration -s

# End-to-end tests
./scripts/run_tests.sh e2e -s -c

# All tests with coverage
./scripts/run_tests.sh all -c -v
```

### Test Reports

Test results are generated in multiple formats:
- HTML reports: `test-reports/report-*.html`
- JUnit XML: `test-reports/junit-*.xml`
- Coverage: `test-reports/coverage-*/index.html`

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**
   ```bash
   # Check API service connectivity
   curl http://localhost:8000/health
   
   # Check Discord bot logs
   docker-compose logs discord-bot
   ```

2. **AI responses empty/poor quality**
   ```bash
   # Check ChromaDB has articles
   curl http://localhost:8000/api/v1/heartbeat
   
   # Monitor LiteLLM gateway logs
   docker-compose logs litellm-gateway
   ```

3. **High latency**
   ```bash
   # Monitor response times
   ./scripts/health_monitor.sh -r
   
   # Check resource usage
   docker stats
   ```

4. **Security alerts**
   ```bash
   # View security events
   curl http://localhost:4000/security/alerts
   
   # Monitor blocked requests
   ./scripts/log_aggregator.py --security-focus
   ```

### Diagnostic Commands

```bash
# System health check
./scripts/health_monitor.sh -a

# Log analysis
./scripts/log_aggregator.py

# Service-specific logs
docker-compose logs -f [service-name]

# API endpoint testing  
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"test","user_id":"test","username":"test"}'
```