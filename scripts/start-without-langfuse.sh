#!/bin/bash

# WoW Actuality Agent Bot - Start without Langfuse
# Use this script to start the application without Langfuse monitoring

set -e

echo "🚀 Starting WoW Actuality Agent Bot (without Langfuse)..."

# Set environment variable to skip Langfuse
export SKIP_LANGFUSE=1

# Run the setup script which will handle the startup
./scripts/setup-first-launch.sh

echo ""
echo "✅ Application started without Langfuse monitoring"
echo "📊 To add Langfuse later, edit .env file and run: docker-compose up -d langfuse"