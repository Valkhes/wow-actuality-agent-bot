#!/bin/bash

# Deploy WoW Actuality Bot to Google Cloud Run
# Usage: ./deploy-to-cloud-run.sh [PROJECT_ID]

set -e

# Configuration
PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION="us-central1"
BUILD_ID=$(date +%Y%m%d-%H%M%S)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID not provided and not set in gcloud config"
    echo "Usage: ./deploy-to-cloud-run.sh PROJECT_ID"
    exit 1
fi

echo "Deploying WoW Actuality Bot to Google Cloud Run"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Build ID: $BUILD_ID"

# Enable required APIs
echo "Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com \
    run.googleapis.com \
    firestore.googleapis.com \
    secretmanager.googleapis.com \
    --project=$PROJECT_ID

# Create secrets (you need to set these values)
echo "Creating secrets..."
echo "Note: You need to manually create these secrets with actual values:"
echo "- google-api-key"
echo "- discord-token" 
echo "- langfuse-keys (with secret_key and public_key)"
echo "- litellm-master-key"

# Check if secrets exist, create placeholders if not
gcloud secrets describe google-api-key --project=$PROJECT_ID 2>/dev/null || {
    echo "Creating placeholder secret for google-api-key..."
    echo -n "REPLACE_WITH_ACTUAL_KEY" | gcloud secrets create google-api-key --data-file=- --project=$PROJECT_ID
}

gcloud secrets describe discord-token --project=$PROJECT_ID 2>/dev/null || {
    echo "Creating placeholder secret for discord-token..."
    echo -n "REPLACE_WITH_ACTUAL_TOKEN" | gcloud secrets create discord-token --data-file=- --project=$PROJECT_ID
}

gcloud secrets describe litellm-master-key --project=$PROJECT_ID 2>/dev/null || {
    echo "Creating placeholder secret for litellm-master-key..."
    echo -n "REPLACE_WITH_ACTUAL_KEY" | gcloud secrets create litellm-master-key --data-file=- --project=$PROJECT_ID
}

# Build and deploy using Cloud Build
echo "Starting Cloud Build deployment..."
gcloud builds submit --config=cloudbuild.yaml \
    --substitutions=_PROJECT_ID=$PROJECT_ID,_BUILD_ID=$BUILD_ID \
    --project=$PROJECT_ID

echo "Deployment completed!"
echo
echo "Next steps:"
echo "1. Update secrets with actual values:"
echo "   gcloud secrets versions add google-api-key --data-file=google-api-key.txt"
echo "   gcloud secrets versions add discord-token --data-file=discord-token.txt"
echo "   gcloud secrets versions add litellm-master-key --data-file=litellm-key.txt"
echo
echo "2. Get service URLs:"
echo "   gcloud run services list --platform=managed --region=$REGION"
echo
echo "3. Update Discord bot API_SERVICE_URL environment variable with actual API service URL"
echo "4. Test the services:"
echo "   - API Service: curl https://wow-api-service-[HASH]-uc.a.run.app/health"
echo "   - Crawler Service: Check logs for crawling activity"