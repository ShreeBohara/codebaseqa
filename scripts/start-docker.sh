#!/bin/bash

# Start CodebaseQA with Docker Compose
echo "🚀 Starting CodebaseQA..."

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running"
  exit 1
fi

# Check for --with-demo flag
if [ "$1" = "--with-demo" ]; then
  echo "📦 Demo mode enabled - will seed demo repository on startup"
  export SEED_DEMO=true
fi

# Build and start
docker-compose -f docker/docker-compose.yml up --build -d

echo "✅ Services started!"
echo "   Web App: http://localhost:3000"
echo "   API:     http://localhost:8000/docs"
echo "   Health:  http://localhost:8000/health"
echo ""
echo "💡 Tips:"
echo "   - Add SEED_DEMO=true to .env or use './scripts/start-docker.sh --with-demo' for demo data"
echo "   - View logs: docker-compose -f docker/docker-compose.yml logs -f"
echo "   - Stop: docker-compose -f docker/docker-compose.yml down"
