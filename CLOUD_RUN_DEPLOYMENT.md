# WoW Actuality Bot - Cloud Run Deployment Guide

This guide will help you deploy the WoW Actuality Bot to Google Cloud Run.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Docker** installed locally
3. **Google Cloud SDK (gcloud)** installed and configured
4. **Required API Keys**:
   - Google API key (for Gemini AI)
   - Discord Bot token
   - LiteLLM master key (optional)
   - Langfuse keys (optional)

## Architecture Changes for Cloud Run

The application has been modified to work with Cloud Run:

- **PostgreSQL** → Removed (Langfuse will use Langfuse Cloud or be skipped)
- **ChromaDB** → **Firestore** (vector storage)
- **File-based cache** → **Firestore** (cache storage)
- **Volume mounts** → Removed
- **Service discovery** → HTTP URLs
- **Logging** → Cloud Logging (stdout)

## Quick Deployment

### Option 1: Automated Deployment

```bash
# Set your Google Cloud project
export PROJECT_ID="your-project-id"

# Run the deployment script
./deploy-to-cloud-run.sh $PROJECT_ID
```

### Option 2: Individual Service Deployment

```bash
# Deploy all services
./deploy-individual-services.sh $PROJECT_ID all

# Or deploy individual services
./deploy-individual-services.sh $PROJECT_ID api
./deploy-individual-services.sh $PROJECT_ID discord
./deploy-individual-services.sh $PROJECT_ID crawler
./deploy-individual-services.sh $PROJECT_ID litellm
```

## Manual Deployment Steps

### 1. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com
```

### 2. Create Secrets

Create the required secrets with your actual values:

```bash
# Google API Key
echo -n "your-actual-google-api-key" | gcloud secrets create google-api-key --data-file=-

# Discord Bot Token
echo -n "your-actual-discord-token" | gcloud secrets create discord-token --data-file=-

# LiteLLM Master Key (optional)
echo -n "your-litellm-master-key" | gcloud secrets create litellm-master-key --data-file=-

# Langfuse Keys (optional)
echo -n "your-langfuse-secret-key" | gcloud secrets create langfuse-secret-key --data-file=-
echo -n "your-langfuse-public-key" | gcloud secrets create langfuse-public-key --data-file=-
```

### 3. Initialize Firestore

```bash
# Create Firestore database in Native mode
gcloud firestore databases create --region=us-central1
```

### 4. Deploy Services

#### LiteLLM Gateway (Deploy First)
```bash
cd litellm-gateway
docker build -t gcr.io/$PROJECT_ID/wow-litellm-gateway:latest .
docker push gcr.io/$PROJECT_ID/wow-litellm-gateway:latest

gcloud run deploy wow-litellm-gateway \
    --image=gcr.io/$PROJECT_ID/wow-litellm-gateway:latest \
    --region=us-central1 \
    --platform=managed \
    --no-allow-unauthenticated \
    --max-instances=3 \
    --memory=512Mi \
    --cpu=1 \
    --set-secrets=LITELLM_MASTER_KEY=litellm-master-key:latest,GOOGLE_API_KEY=google-api-key:latest
```

#### API Service
```bash
cd api-service
docker build -t gcr.io/$PROJECT_ID/wow-api-service:latest .
docker push gcr.io/$PROJECT_ID/wow-api-service:latest

gcloud run deploy wow-api-service \
    --image=gcr.io/$PROJECT_ID/wow-api-service:latest \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated \
    --max-instances=10 \
    --memory=1Gi \
    --cpu=1 \
    --set-env-vars=VECTOR_STORE_TYPE=firestore,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID \
    --set-secrets=GOOGLE_API_KEY=google-api-key:latest
```

#### Crawler Service
```bash
cd crawler-service
docker build -t gcr.io/$PROJECT_ID/wow-crawler-service:latest .
docker push gcr.io/$PROJECT_ID/wow-crawler-service:latest

gcloud run deploy wow-crawler-service \
    --image=gcr.io/$PROJECT_ID/wow-crawler-service:latest \
    --region=us-central1 \
    --platform=managed \
    --no-allow-unauthenticated \
    --max-instances=1 \
    --memory=1Gi \
    --cpu=1 \
    --timeout=3600 \
    --set-env-vars=VECTOR_STORE_TYPE=firestore,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID
```

#### Discord Bot
```bash
# Get API service URL first
API_URL=$(gcloud run services describe wow-api-service --region=us-central1 --format="value(status.url)")

cd discord-bot
docker build -t gcr.io/$PROJECT_ID/wow-discord-bot:latest .
docker push gcr.io/$PROJECT_ID/wow-discord-bot:latest

gcloud run deploy wow-discord-bot \
    --image=gcr.io/$PROJECT_ID/wow-discord-bot:latest \
    --region=us-central1 \
    --platform=managed \
    --no-allow-unauthenticated \
    --max-instances=1 \
    --memory=512Mi \
    --cpu=0.5 \
    --timeout=600 \
    --set-env-vars=API_SERVICE_URL=$API_URL \
    --set-secrets=DISCORD_BOT_TOKEN=discord-token:latest
```

## Configuration

### Environment Variables

Each service can be configured with these environment variables:

**API Service:**
- `VECTOR_STORE_TYPE=firestore`
- `GOOGLE_CLOUD_PROJECT_ID=your-project-id`
- `LANGFUSE_HOST=https://cloud.langfuse.com` (optional)

**Discord Bot:**
- `API_SERVICE_URL=https://your-api-service-url`
- `RATE_LIMIT_REQUESTS_PER_MINUTE=10`
- `MAX_QUESTION_LENGTH=500`

**Crawler Service:**
- `VECTOR_STORE_TYPE=firestore`
- `GOOGLE_CLOUD_PROJECT_ID=your-project-id`
- `CRAWLER_INTERVAL_HOURS=6`
- `CRAWLER_MAX_ARTICLES=50`

### Secrets

All secrets are stored in Google Secret Manager:
- `google-api-key`: Your Google AI API key
- `discord-token`: Your Discord bot token
- `litellm-master-key`: Master key for LiteLLM gateway
- `langfuse-secret-key`: Langfuse secret key (optional)
- `langfuse-public-key`: Langfuse public key (optional)

## Monitoring and Logs

### View Logs
```bash
# API Service logs
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=wow-api-service"

# Discord Bot logs
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=wow-discord-bot"

# Crawler logs
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=wow-crawler-service"
```

### Health Checks
```bash
# Test API service
API_URL=$(gcloud run services describe wow-api-service --region=us-central1 --format="value(status.url)")
curl $API_URL/health

# Test LiteLLM gateway
LITELLM_URL=$(gcloud run services describe wow-litellm-gateway --region=us-central1 --format="value(status.url)")
curl $LITELLM_URL/health
```

## Cost Optimization

- **API Service**: Scales to zero when not used
- **Discord Bot**: Runs continuously (minimal cost)
- **Crawler Service**: Runs periodically (6-hour intervals)
- **LiteLLM Gateway**: Scales to zero when not used

Expected monthly cost: $5-20 for light usage.

## Troubleshooting

### Common Issues

1. **Firestore permissions**: Ensure Cloud Run services have Firestore access
2. **Secret access**: Verify secrets are created and accessible
3. **API quotas**: Monitor Google AI API usage
4. **Cold starts**: First requests may be slow (~30 seconds)

### Debug Commands

```bash
# Check service status
gcloud run services list --platform=managed

# View service details
gcloud run services describe SERVICE_NAME --region=us-central1

# Check recent deployments
gcloud run revisions list --service=SERVICE_NAME --region=us-central1
```

## Updating Services

To update a service after code changes:

```bash
# Rebuild and redeploy
./deploy-individual-services.sh $PROJECT_ID SERVICE_NAME
```

## Cleanup

To delete all services:

```bash
gcloud run services delete wow-api-service --region=us-central1
gcloud run services delete wow-discord-bot --region=us-central1
gcloud run services delete wow-crawler-service --region=us-central1
gcloud run services delete wow-litellm-gateway --region=us-central1
```