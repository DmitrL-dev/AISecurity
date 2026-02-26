# SENTINEL Shield Docker Image
# Multi-stage build: compile with gcc, run on minimal Alpine

# ============ BUILD STAGE ============
FROM alpine:3.19 AS builder

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    openssl-dev \
    linux-headers \
    pcre-dev

# Copy source
WORKDIR /build
COPY include/ ./include/
COPY src/ ./src/
COPY Makefile ./

# Build (Linux variant)
RUN make clean 2>/dev/null || true && make

# ============ RUNTIME STAGE ============
FROM alpine:3.19

# Install runtime dependencies
RUN apk add --no-cache \
    libstdc++ \
    openssl \
    pcre

# Create non-root user
RUN addgroup -S shield && adduser -S shield -G shield

# Create directories
RUN mkdir -p /opt/shield/lib /etc/shield /var/log/shield \
    && chown -R shield:shield /opt/shield /var/log/shield

WORKDIR /opt/shield

# Copy built artifacts from builder
COPY --from=builder /build/build/libshield.so /opt/shield/lib/
COPY --from=builder /build/build/libshield.a /opt/shield/lib/

# Copy default config if exists
COPY --chmod=644 config/*.json /etc/shield/ 2>/dev/null || true

# Set library path
ENV LD_LIBRARY_PATH=/opt/shield/lib

# Switch to non-root user
USER shield

# Expose ports (API: 8080, Metrics: 9090)
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD test -f /opt/shield/lib/libshield.so || exit 1

# Labels
LABEL org.opencontainers.image.title="SENTINEL Shield"
LABEL org.opencontainers.image.description="AI Security Shield - Enterprise LLM Protection"
LABEL org.opencontainers.image.version="1.2.0"
LABEL org.opencontainers.image.vendor="SENTINEL Project"
LABEL org.opencontainers.image.source="https://github.com/SENTINEL/shield"

# Default: library mode (no daemon, use as base image)
CMD ["echo", "SENTINEL Shield library ready. Mount your application or use as base image."]
