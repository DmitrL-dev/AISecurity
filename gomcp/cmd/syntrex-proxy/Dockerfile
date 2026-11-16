FROM golang:1.26.10-alpine@sha256:87c65a688975c0b1d4585d204874c45ca78354670e3a5f11368c5a492303d696 AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /syntrex-proxy ./cmd/syntrex-proxy/

FROM alpine:3.19
RUN apk add --no-cache ca-certificates
COPY --from=builder /syntrex-proxy /usr/local/bin/syntrex-proxy
EXPOSE 8080
ENTRYPOINT ["syntrex-proxy"]
CMD ["--listen", ":8080", "--target", "https://api.openai.com", "--mode", "block"]
