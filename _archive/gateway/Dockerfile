FROM golang:alpine AS builder

WORKDIR /app

# Copy go.mod and download dependencies
COPY go.mod ./
RUN go mod download || true

# Copy source and regenerate go.sum
COPY . .
RUN go mod tidy
RUN go build -o sentinel-gateway ./cmd/main.go

FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/sentinel-gateway .

# Copy dashboard static files
COPY dashboard/ ./dashboard/

# Create certs directory (will be mounted via volume)
RUN mkdir -p /certs

EXPOSE 8080

CMD ["./sentinel-gateway"]

