FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy production requirements (slim, CPU-only)
COPY requirements-pro.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-pro.txt

# Copy source code
COPY src/ src/
COPY config/ config/

# Set PYTHONPATH
ENV PYTHONPATH="/app:/app/src/brain:$PYTHONPATH"

# Railway uses PORT env variable
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run API server — Railway sets PORT automatically
CMD uvicorn src.brain.api.main:app --host 0.0.0.0 --port ${PORT}
