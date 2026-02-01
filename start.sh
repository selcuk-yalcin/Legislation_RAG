#!/bin/bash
set -e

echo "🚀 Starting Legislation RAG System..."

# Get PORT from environment, default to 8080
PORT="${PORT:-8080}"
echo "📍 Using PORT: $PORT"

# Start gunicorn
exec gunicorn app:app \
  --bind "0.0.0.0:$PORT" \
  --workers 1 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
