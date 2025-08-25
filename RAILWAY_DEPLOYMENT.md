# Railway Deployment Guide

## Services Overview
Deploy these 7 services on Railway:

### 1. PostgreSQL (Railway Add-on)
- **Type**: Railway PostgreSQL add-on
- **Purpose**: Database for Langfuse

### 2. ChromaDB Service
- **Docker Image**: `chromadb/chroma:latest`
- **Port**: 8000
- **Environment Variables**:
  ```
  IS_PERSISTENT=TRUE
  PERSIST_DIRECTORY=/chroma/chroma
  ```
- **Volume**: Mount persistent volume to `/chroma/chroma`

### 3. Langfuse Service  
- **Docker Image**: `langfuse/langfuse:2`
- **Port**: 3000
- **Environment Variables**:
  ```
  DATABASE_URL=${{ Postgres.DATABASE_URL }}
  NEXTAUTH_SECRET=your_secret_key_here
  NEXTAUTH_URL=https://your-langfuse-service.up.railway.app
  SALT=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
  LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=true
  ```

### 4. LiteLLM Gateway
- **Dockerfile**: `./litellm-gateway/Dockerfile`  
- **Port**: Railway assigns dynamically (uses PORT env var)
- **Environment Variables**:
  ```
  LITELLM_MASTER_KEY=your_master_key
  GOOGLE_API_KEY=your_google_api_key
  LOG_LEVEL=INFO
  ENVIRONMENT=production
  ```

### 5. API Service
- **Dockerfile**: `./api-service/Dockerfile`
- **Port**: Railway assigns dynamically (uses PORT env var)  
- **Environment Variables**:
  ```
  GOOGLE_API_KEY=your_google_api_key
  CHROMADB_HOST=https://your-chromadb-service.up.railway.app
  CHROMADB_PORT=443
  LITELLM_GATEWAY_URL=https://your-litellm-service.up.railway.app
  LANGFUSE_SECRET_KEY=your_langfuse_secret
  LANGFUSE_PUBLIC_KEY=your_langfuse_public
  LANGFUSE_HOST=https://your-langfuse-service.up.railway.app
  LOG_LEVEL=INFO
  ENVIRONMENT=production
  ```

### 6. Crawler Service
- **Dockerfile**: `./crawler-service/Dockerfile`
- **Port**: Railway assigns dynamically (uses PORT env var)
- **Environment Variables**:
  ```
  CHROMADB_HOST=https://your-chromadb-service.up.railway.app
  CHROMADB_PORT=443
  BLIZZSPIRIT_BASE_URL=https://www.blizzspirit.com
  CRAWLER_INTERVAL_HOURS=6
  CRAWLER_MAX_ARTICLES=100
  LOG_LEVEL=INFO
  ENVIRONMENT=production
  ```
- **Volume**: Mount persistent volume to `/app/cache`

### 7. Discord Bot
- **Dockerfile**: `./discord-bot/Dockerfile`
- **Port**: None (no HTTP server)
- **Environment Variables**:
  ```
  DISCORD_BOT_TOKEN=your_discord_bot_token
  API_SERVICE_URL=https://your-api-service.up.railway.app
  LOG_LEVEL=INFO
  ENVIRONMENT=production
  RATE_LIMIT_REQUESTS_PER_MINUTE=60
  MAX_QUESTION_LENGTH=500
  ```

## Deployment Steps

1. **Create PostgreSQL Add-on** in Railway
2. **Deploy ChromaDB** with persistent volume
3. **Deploy Langfuse** (connect to PostgreSQL)
4. **Deploy LiteLLM Gateway** 
5. **Deploy API Service** (connect to ChromaDB + LiteLLM)
6. **Deploy Crawler Service** (connect to ChromaDB)
7. **Deploy Discord Bot** (connect to API Service)

## Important Notes

- Replace all `your-service-name` placeholders with actual Railway service URLs
- Use HTTPS URLs for inter-service communication
- Set `CHROMADB_PORT=443` when using HTTPS
- Railway automatically handles SSL certificates
- No Docker Compose networking needed - use public service URLs
- All services use Railway's dynamic PORT environment variable