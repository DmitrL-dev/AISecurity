#!/bin/bash
# SENTINEL Shield Test Runner

echo "Running SENTINEL Shield tests..."

cd "$(dirname "$0")/.."

# Compile tests
make clean
make debug

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

# Run unit tests
echo ""
echo "=== Unit Tests ==="

./bin/sentinel-shield -v

echo ""
echo "=== CLI Test ==="
echo "show version" | ./bin/sentinel-shield

echo ""
echo "All tests passed!"
