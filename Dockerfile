# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (cached layer)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    curl

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy source code
COPY src/ src/
COPY config/ config/

# Set PYTHONPATH to include /app and /app/src/brain for proper imports
# - /app: for src.brain.* imports
# - /app/src/brain: for engines.* imports
ENV PYTHONPATH="/app:/app/src/brain:$PYTHONPATH"

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run API server
CMD ["uvicorn", "src.brain.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
