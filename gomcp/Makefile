.PHONY: build test lint clean cover cross all check build-soc test-soc bench-soc ci

VERSION ?= $(shell grep 'Version.*=' internal/application/tools/system_service.go | head -1 | cut -d'"' -f2)
BINARY = gomcp
SOC_BINARY = syntrex-soc
LDFLAGS = -ldflags "-X github.com/sentinel-community/gomcp/internal/application/tools.Version=$(VERSION) \
	-X github.com/sentinel-community/gomcp/internal/application/tools.GitCommit=$(shell git rev-parse --short HEAD 2>/dev/null || echo unknown) \
	-X github.com/sentinel-community/gomcp/internal/application/tools.BuildDate=$(shell date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"

# --- Build ---

build:
	go build $(LDFLAGS) -o $(BINARY) ./cmd/gomcp/

build-soc:
	go build $(LDFLAGS) -o $(SOC_BINARY) ./cmd/soc/

build-all:
	go build ./...

build-windows:
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY)-windows-amd64.exe ./cmd/gomcp/

build-linux:
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY)-linux-amd64 ./cmd/gomcp/

build-darwin:
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY)-darwin-arm64 ./cmd/gomcp/

cross: build-windows build-linux build-darwin

# --- Test ---

test:
	go test ./... -count=1 -timeout 60s -coverprofile=coverage.out

test-soc:
	go test ./internal/domain/soc/... ./internal/application/soc/... ./internal/transport/http/... -count=1 -timeout 30s -v

test-race:
	go test ./... -race -count=1 -timeout 120s

cover: test
	go tool cover -func=coverage.out

cover-html: test
	go tool cover -html=coverage.out -o coverage.html

bench-soc:
	go test ./internal/domain/soc/... -bench=. -benchmem -count=3

# --- Lint ---

lint:
	golangci-lint run ./...

fmt:
	go fmt ./...

vet:
	go vet ./...

# --- Quality gate (lint + test + build) ---

check: lint test build

# --- CI pipeline (fmt → vet → test → build) ---

ci: fmt vet test build-all
	@echo "CI pipeline complete ✓"

# --- Docker ---

docker-soc:
	docker build -t syntrex/soc:$(VERSION) -f Dockerfile .
	docker tag syntrex/soc:$(VERSION) syntrex/soc:latest

# --- Run ---

run-soc:
	SOC_PORT=9100 SOC_DB_PATH=soc-dev.db go run ./cmd/soc/

# --- Clean ---

clean:
	rm -f $(BINARY) $(SOC_BINARY) $(BINARY)-*.exe $(BINARY)-linux-* $(BINARY)-darwin-* coverage.out coverage.html *.db

