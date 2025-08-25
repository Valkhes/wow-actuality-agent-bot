#!/bin/bash

# Deploy individual services to Google Cloud Run
# Usage: ./deploy-individual-services.sh [PROJECT_ID] [SERVICE_NAME]
# SERVICE_NAME can be: api, discord, crawler, litellm, or all

set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}
SERVICE_NAME=${2:-"all"}
REGION="us-central1"
BUILD_ID=$(date +%Y%m%d-%H%M%S)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID not provided and not set in gcloud config"
    echo "Usage: ./deploy-individual-services.sh PROJECT_ID [SERVICE_NAME]"
    exit 1
fi

echo "Deploying services to Google Cloud Run"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

deploy_api_service() {
    echo "Deploying API Service..."
    
    # Build image
    docker build -t gcr.io/$PROJECT_ID/wow-api-service:$BUILD_ID ./api-service
    docker push gcr.io/$PROJECT_ID/wow-api-service:$BUILD_ID
    
    # Deploy to Cloud Run
    gcloud run deploy wow-api-service \
        --image=gcr.io/$PROJECT_ID/wow-api-service:$BUILD_ID \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --max-instances=10 \
        --memory=1Gi \
        --cpu=1 \
        --concurrency=1000 \
        --timeout=300 \
        --set-env-vars=VECTOR_STORE_TYPE=firestore,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID \
        --set-secrets=GOOGLE_API_KEY=google-api-key:latest \
        --project=$PROJECT_ID
    
    echo "API Service deployed successfully!"
}

deploy_discord_service() {
    echo "Deploying Discord Bot Service..."
    
    # Get API service URL
    API_URL=$(gcloud run services describe wow-api-service --region=$REGION --format="value(status.url)" --project=$PROJECT_ID 2>/dev/null || echo "UPDATE_ME")
    
    # Build image
    docker build -t gcr.io/$PROJECT_ID/wow-discord-bot:$BUILD_ID ./discord-bot
    docker push gcr.io/$PROJECT_ID/wow-discord-bot:$BUILD_ID
    
    # Deploy to Cloud Run
    gcloud run deploy wow-discord-bot \
        --image=gcr.io/$PROJECT_ID/wow-discord-bot:$BUILD_ID \
        --region=$REGION \
        --platform=managed \
        --no-allow-unauthenticated \
        --max-instances=1 \
        --memory=512Mi \
        --cpu=0.5 \
        --concurrency=1 \
        --timeout=600 \
        --set-env-vars=API_SERVICE_URL=$API_URL \
        --set-secrets=DISCORD_BOT_TOKEN=discord-token:latest \
        --project=$PROJECT_ID
    
    echo "Discord Bot Service deployed successfully!"
}

deploy_crawler_service() {
    echo "Deploying Crawler Service..."
    
    # Build image
    docker build -t gcr.io/$PROJECT_ID/wow-crawler-service:$BUILD_ID ./crawler-service
    docker push gcr.io/$PROJECT_ID/wow-crawler-service:$BUILD_ID
    
    # Deploy to Cloud Run
    gcloud run deploy wow-crawler-service \
        --image=gcr.io/$PROJECT_ID/wow-crawler-service:$BUILD_ID \
        --region=$REGION \
        --platform=managed \
        --no-allow-unauthenticated \
        --max-instances=1 \
        --memory=1Gi \
        --cpu=1 \
        --concurrency=1 \
        --timeout=3600 \
        --set-env-vars=VECTOR_STORE_TYPE=firestore,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID \
        --project=$PROJECT_ID
    
    echo "Crawler Service deployed successfully!"
}

deploy_litellm_service() {
    echo "Deploying LiteLLM Gateway Service..."
    
    # Build image
    docker build -t gcr.io/$PROJECT_ID/wow-litellm-gateway:$BUILD_ID ./litellm-gateway
    docker push gcr.io/$PROJECT_ID/wow-litellm-gateway:$BUILD_ID
    
    # Deploy to Cloud Run
    gcloud run deploy wow-litellm-gateway \
        --image=gcr.io/$PROJECT_ID/wow-litellm-gateway:$BUILD_ID \
        --region=$REGION \
        --platform=managed \
        --no-allow-unauthenticated \
        --max-instances=3 \
        --memory=512Mi \
        --cpu=1 \
        --concurrency=1000 \
        --timeout=300 \
        --set-secrets=LITELLM_MASTER_KEY=litellm-master-key:latest,GOOGLE_API_KEY=google-api-key:latest \
        --project=$PROJECT_ID
    
    echo "LiteLLM Gateway Service deployed successfully!"
}

# Deploy based on service name
case $SERVICE_NAME in
    "api")
        deploy_api_service
        ;;
    "discord")
        deploy_discord_service
        ;;
    "crawler")
        deploy_crawler_service
        ;;
    "litellm")
        deploy_litellm_service
        ;;
    "all")
        deploy_litellm_service
        deploy_api_service
        deploy_crawler_service
        deploy_discord_service
        ;;
    *)
        echo "Unknown service: $SERVICE_NAME"
        echo "Available services: api, discord, crawler, litellm, all"
        exit 1
        ;;
esac

echo "Deployment completed!"
echo
echo "Service URLs:"
gcloud run services list --platform=managed --region=$REGION --project=$PROJECT_ID