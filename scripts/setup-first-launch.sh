#!/bin/bash

# WoW Actuality Agent Bot - First Launch Setup Script
# This script handles all the initial setup and configuration

set -e

echo "🚀 Starting WoW Actuality Agent Bot First Launch Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.template .env
    print_success "Created .env file from template"
    print_warning "Please edit the .env file with your actual API keys and configuration!"
fi

# Generate random secrets if they're using defaults
if grep -q "your_secret_key_here" .env; then
    print_status "Generating random secrets for production use..."
    
    # Generate random SALT (64 hex characters = 256 bits)
    RANDOM_SALT=$(openssl rand -hex 32)
    sed -i.bak "s/your_secret_key_here/$RANDOM_SALT/g" .env
    
    # Generate random master key
    RANDOM_MASTER_KEY=$(openssl rand -hex 16)
    sed -i.bak "s/your_master_key/$RANDOM_MASTER_KEY/g" .env
    
    print_success "Generated random secrets in .env file"
fi

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Remove old volumes to ensure fresh start (optional - commented out by default)
# print_warning "Removing old data volumes for fresh start..."
# docker volume rm wow-actuality-agent-bot_postgres_data 2>/dev/null || true
# docker volume rm wow-actuality-agent-bot_chromadb_data 2>/dev/null || true

# Build and start core services first
print_status "Building and starting core infrastructure services..."
docker-compose up -d postgres chromadb

# Wait for PostgreSQL to be ready
print_status "Waiting for PostgreSQL to initialize..."
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    if docker exec wow-postgres pg_isready -U wowbot -d postgres >/dev/null 2>&1; then
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

if [ $counter -ge $timeout ]; then
    print_error "PostgreSQL failed to start within $timeout seconds"
    exit 1
fi

print_success "PostgreSQL is ready"

# Verify databases were created
print_status "Verifying database setup..."
if docker exec wow-postgres psql -U wowbot -lqt | cut -d \| -f 1 | grep -qw wowactuality; then
    print_success "Database 'wowactuality' exists"
else
    print_warning "Creating 'wowactuality' database..."
    docker exec wow-postgres psql -U wowbot -c "CREATE DATABASE wowactuality;" postgres
fi

if docker exec wow-postgres psql -U wowbot -lqt | cut -d \| -f 1 | grep -qw wowbot; then
    print_success "Database 'wowbot' exists"
else
    print_warning "Creating 'wowbot' database..."
    docker exec wow-postgres psql -U wowbot -c "CREATE DATABASE wowbot;" postgres
fi

# Wait for ChromaDB to be ready
print_status "Waiting for ChromaDB to be ready..."
timeout=30
counter=0
while [ $counter -lt $timeout ]; do
    if curl -s -f http://localhost:8000 >/dev/null 2>&1; then
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

if [ $counter -ge $timeout ]; then
    print_warning "ChromaDB took longer than expected to start, but continuing..."
else
    print_success "ChromaDB is ready"
fi

# Start LiteLLM Gateway
print_status "Starting LiteLLM Gateway..."
docker-compose up -d litellm-gateway

# Wait for LiteLLM Gateway
print_status "Waiting for LiteLLM Gateway..."
timeout=30
counter=0
while [ $counter -lt $timeout ]; do
    if curl -s -f http://localhost:4000/health >/dev/null 2>&1; then
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

if [ $counter -ge $timeout ]; then
    print_warning "LiteLLM Gateway took longer than expected to start"
else
    print_success "LiteLLM Gateway is ready"
fi

# Start Langfuse (optional)
if [ -z "$SKIP_LANGFUSE" ]; then
    print_status "Starting Langfuse monitoring..."
    docker-compose up -d langfuse
    print_success "Langfuse started (may take a few minutes to be fully ready)"
else
    print_warning "Skipping Langfuse (SKIP_LANGFUSE is set)"
fi

# Start application services
print_status "Starting application services..."
docker-compose up -d api-service discord-bot crawler-service

print_success "🎉 First launch setup completed!"
print_status "Services status:"
docker-compose ps

echo ""
print_status "📋 Next steps:"
echo "1. Edit .env file with your API keys (Discord, Google AI, etc.)"
echo "2. Check service logs: docker-compose logs [service-name]"
echo "3. Access services:"
echo "   - API Service: http://localhost:8000"
echo "   - Langfuse: http://localhost:3000 (if enabled)"
echo "   - ChromaDB: http://localhost:8000"
echo "   - LiteLLM Gateway: http://localhost:4000"
echo ""
print_status "🔧 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Restart services: docker-compose restart"
echo "   - Stop all: docker-compose down"
echo ""