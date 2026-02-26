.PHONY: build test lint clean cover cross all check

VERSION ?= $(shell grep 'Version.*=' internal/application/tools/system_service.go | head -1 | cut -d'"' -f2)
BINARY = gomcp
LDFLAGS = -ldflags "-X github.com/sentinel-community/gomcp/internal/application/tools.Version=$(VERSION) \
	-X github.com/sentinel-community/gomcp/internal/application/tools.GitCommit=$(shell git rev-parse --short HEAD 2>/dev/null || echo unknown) \
	-X github.com/sentinel-community/gomcp/internal/application/tools.BuildDate=$(shell date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"

# --- Build ---

build:
	go build $(LDFLAGS) -o $(BINARY) ./cmd/gomcp/

build-windows:
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY)-windows-amd64.exe ./cmd/gomcp/

build-linux:
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BINARY)-linux-amd64 ./cmd/gomcp/

build-darwin:
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BINARY)-darwin-arm64 ./cmd/gomcp/

cross: build-windows build-linux build-darwin

# --- Test ---

test:
	go test ./... -v -count=1 -coverprofile=coverage.out

test-race:
	go test ./... -v -race -count=1

cover: test
	go tool cover -func=coverage.out

cover-html: test
	go tool cover -html=coverage.out -o coverage.html

# --- Lint ---

lint:
	golangci-lint run ./...

# --- Quality gate (lint + test + build) ---

check: lint test build

# --- Clean ---

clean:
	rm -f $(BINARY) $(BINARY)-*.exe $(BINARY)-linux-* $(BINARY)-darwin-* coverage.out coverage.html

all: check cross
