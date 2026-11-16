# syntax=docker/dockerfile:1
# Syntrex GoMCP — Multi-stage build

# ─── Build stage ────────────────────────────────────
FROM golang:1.26.10-alpine@sha256:87c65a688975c0b1d4585d204874c45ca78354670e3a5f11368c5a492303d696 AS builder

RUN apk add --no-cache ca-certificates tzdata

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .

# Build static binary (modernc/sqlite = pure Go, no CGO needed).
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /gomcp ./cmd/gomcp

# ─── Runtime stage ──────────────────────────────────
FROM alpine:3.20

RUN apk add --no-cache ca-certificates

WORKDIR /app
COPY --from=builder /gomcp /app/gomcp

RUN addgroup -S syntrex && adduser -S syntrex -G syntrex
RUN mkdir -p /data/.rlm && chown -R syntrex:syntrex /data
USER syntrex

EXPOSE 9750

ENV RLM_DIR=/data/.rlm
ENV GOMCP_HTTP_PORT=9750

ENTRYPOINT ["/app/gomcp"]
CMD ["--http-port", "9750"]
