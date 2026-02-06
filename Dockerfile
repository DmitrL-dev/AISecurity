# syntax=docker/dockerfile:1.4
# ============================================================
# SENTINEL Brain - Multi-stage build with Rust Core
# ============================================================

# -------------------- Stage 1: Rust Builder --------------------
FROM rust:1.85-slim AS rust-builder

# Install maturin and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install maturin --break-system-packages

WORKDIR /build

# Copy Cargo files first for dependency caching
COPY sentinel-core/Cargo.toml sentinel-core/Cargo.lock ./
COPY sentinel-core/pyproject.toml sentinel-core/README.md ./
COPY sentinel-core/benches ./benches

# Create dummy src for dependency build
RUN mkdir -p src && echo "fn main() {}" > src/lib.rs

# Pre-build dependencies (cached layer)
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/build/target \
    cargo fetch

# Now copy actual source
COPY sentinel-core/src ./src

# Build wheel with maturin (uses cached dependencies)
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/build/target \
    maturin build --release --strip \
    --interpreter python3.11 \
    --out /wheels

# -------------------- Stage 2: Python Runtime --------------------
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (cached layer)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Install Rust core wheel from builder stage
COPY --from=rust-builder /wheels/*.whl /tmp/
RUN pip install /tmp/sentinel_core-*.whl && rm -rf /tmp/*.whl

# Copy source code
COPY src/ src/
COPY config/ config/

# Set PYTHONPATH to include /app/src so 'brain' is a valid package
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Enable Rust engine by default, disable QwenGuard (replaced by ONNX)
ENV USE_RUST_ENGINE=true
ENV RUST_ROLLOUT_PERCENT=100
ENV QWEN_GUARD_ENABLED=false

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run API server
CMD ["uvicorn", "src.brain.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
