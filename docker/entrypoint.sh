#!/bin/bash
set -e

echo "Starting CodebaseQA API..."

# Check if SEED_DEMO is set to true
if [ "$SEED_DEMO" = "true" ]; then
    echo "Checking for demo data..."
    
    # Check if demo already exists (--check-only exits 0 if demo ready)
    if python -m src.demo.seed_demo --check-only 2>/dev/null; then
        echo "Demo data already available."
    else
        echo "Seeding demo data in background..."
        # Run seed in background with --no-wait so server starts immediately
        python -m src.demo.seed_demo --no-wait &
    fi
fi

# Start the server
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
