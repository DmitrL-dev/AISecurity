# SENTINEL Shield Docker Image
FROM alpine:3.19 AS builder

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    cmake \
    openssl-dev \
    linux-headers

# Copy source
WORKDIR /build
COPY . .

# Build
RUN mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DBUILD_TESTS=OFF \
    -DBUILD_EXAMPLES=OFF \
    -DUSE_OPENSSL=ON \
    .. && \
    make -j$(nproc)

# Runtime image
FROM alpine:3.19

# Install runtime dependencies
RUN apk add --no-cache \
    libstdc++ \
    openssl

# Copy binary
COPY --from=builder /build/build/shield /usr/local/bin/shield

# Copy config
COPY config/example.json /etc/shield/config.json

# Create non-root user
RUN addgroup -S shield && adduser -S shield -G shield
USER shield

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget -q --spider http://localhost:8080/health || exit 1

# Entry point
ENTRYPOINT ["shield"]
CMD ["-c", "/etc/shield/config.json"]
