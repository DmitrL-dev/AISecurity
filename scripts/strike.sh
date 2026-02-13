#!/bin/bash
# SENTINEL Strike - Quick Run Script
# Usage: ./strike.sh https://target.com

set -e

IMAGE_NAME="sentinel-strike:latest"
REPORTS_DIR="./reports"

# Ensure reports directory exists
mkdir -p "$REPORTS_DIR"

# Check if image exists, build if not
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    echo "🔨 Building Strike image..."
    docker build -f Dockerfile.strike -t "$IMAGE_NAME" .
fi

# Run Strike
echo "🐉 Starting SENTINEL Strike..."
docker run --rm \
    -v "$(pwd)/reports:/app/reports" \
    -v "$(pwd)/signatures:/app/signatures:ro" \
    -e GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    --network host \
    "$IMAGE_NAME" "$@"
