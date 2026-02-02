#!/bin/bash

# Start CodebaseQA with Docker Compose
echo "🚀 Starting CodebaseQA..."

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running"
  exit 1
fi

# Build and start
docker-compose -f docker/docker-compose.yml up --build -d

echo "✅ Services started!"
echo "   Web App: http://localhost:3000"
echo "   API:     http://localhost:8000/docs"
echo ""
echo "Type 'docker-compose -f docker/docker-compose.yml logs -f' to view logs"
