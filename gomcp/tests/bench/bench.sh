#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
#  SENTINEL SOC — Performance Baseline (wrk2 / vegeta)
# ═══════════════════════════════════════════════════════
# Usage:
#   ./bench.sh [SOC_URL]        (default: http://localhost:9100)
#
# Requires: wrk2 or vegeta + jq
# pprof: SOC_PPROF=true go run ./cmd/soc/
# ═══════════════════════════════════════════════════════
set -euo pipefail

SOC="${1:-http://localhost:9100}"
DURATION="30s"
RATE=500  # requests/sec target
CONNECTIONS=10

echo "═══════════════════════════════════════════════════"
echo "  SENTINEL SOC — Performance Benchmark"
echo "  Target: $SOC"
echo "  Duration: $DURATION | Rate: ${RATE} rps"
echo "═══════════════════════════════════════════════════"

# ── Health check ──
echo -e "\n[0] Health check..."
curl -sf "${SOC}/healthz" | jq . || { echo "FAIL: server not running"; exit 1; }

# ── Seed test data ──
echo -e "\n[1] Seeding test events..."
for i in $(seq 1 100); do
  curl -sf -X POST "${SOC}/api/soc/events" \
    -H "Content-Type: application/json" \
    -d "{
      \"source\": \"bench-sensor-$((i % 5))\",
      \"severity\": \"MEDIUM\",
      \"category\": \"prompt_injection\",
      \"description\": \"Benchmark test event $i\",
      \"confidence\": 0.$((RANDOM % 100))
    }" > /dev/null 2>&1 || true
done
echo "  Seeded 100 events"

# ── Benchmark: Read Events (GET) ──
echo -e "\n[2] GET /api/soc/events (read throughput)..."
if command -v wrk2 &>/dev/null; then
  wrk2 -t2 -c${CONNECTIONS} -d${DURATION} -R${RATE} \
    --latency "${SOC}/api/soc/events?limit=50"
elif command -v vegeta &>/dev/null; then
  echo "GET ${SOC}/api/soc/events?limit=50" | \
    vegeta attack -duration=${DURATION} -rate=${RATE}/1s -workers=${CONNECTIONS} | \
    vegeta report
else
  echo "  [fallback] Using curl loop (install wrk2 or vegeta for proper benchmarks)"
  START=$(date +%s%N)
  for i in $(seq 1 500); do
    curl -sf "${SOC}/api/soc/events?limit=50" > /dev/null 2>&1
  done
  END=$(date +%s%N)
  ELAPSED=$(( (END - START) / 1000000 ))
  echo "  500 requests in ${ELAPSED}ms ($(( 500000 / ELAPSED )) rps)"
fi

# ── Benchmark: Ingest Events (POST) ──
echo -e "\n[3] POST /api/soc/events (ingest throughput)..."
PAYLOAD='{"source":"bench","severity":"LOW","category":"anomaly","description":"Bench ingest","confidence":0.5}'

if command -v wrk2 &>/dev/null; then
  wrk2 -t2 -c${CONNECTIONS} -d${DURATION} -R${RATE} \
    --latency -s /dev/stdin "${SOC}/api/soc/events" <<'LUA'
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = '{"source":"bench","severity":"LOW","category":"anomaly","description":"Bench ingest","confidence":0.5}'
LUA
elif command -v vegeta &>/dev/null; then
  jq -n --arg url "${SOC}/api/soc/events" --arg body "$PAYLOAD" \
    '{method: "POST", url: $url, body: $body, header: {"Content-Type": ["application/json"]}}' | \
    vegeta attack -duration=${DURATION} -rate=${RATE}/1s -workers=${CONNECTIONS} -format=json | \
    vegeta report
else
  echo "  [fallback] curl loop"
  START=$(date +%s%N)
  for i in $(seq 1 500); do
    curl -sf -X POST "${SOC}/api/soc/events" \
      -H "Content-Type: application/json" -d "$PAYLOAD" > /dev/null 2>&1
  done
  END=$(date +%s%N)
  ELAPSED=$(( (END - START) / 1000000 ))
  echo "  500 POSTs in ${ELAPSED}ms ($(( 500000 / ELAPSED )) rps)"
fi

# ── Benchmark: Dashboard (aggregation) ──
echo -e "\n[4] GET /api/soc/dashboard (aggregation)..."
if command -v wrk2 &>/dev/null; then
  wrk2 -t2 -c${CONNECTIONS} -d${DURATION} -R$(( RATE / 2 )) \
    --latency "${SOC}/api/soc/dashboard"
elif command -v vegeta &>/dev/null; then
  echo "GET ${SOC}/api/soc/dashboard" | \
    vegeta attack -duration=${DURATION} -rate=$(( RATE / 2 ))/1s -workers=${CONNECTIONS} | \
    vegeta report
else
  START=$(date +%s%N)
  for i in $(seq 1 200); do
    curl -sf "${SOC}/api/soc/dashboard" > /dev/null 2>&1
  done
  END=$(date +%s%N)
  ELAPSED=$(( (END - START) / 1000000 ))
  echo "  200 requests in ${ELAPSED}ms ($(( 200000 / ELAPSED )) rps)"
fi

# ── pprof reminder ──
echo -e "\n═══════════════════════════════════════════════════"
echo "  pprof (if SOC_PPROF=true):"
echo "    go tool pprof ${SOC}/debug/pprof/profile?seconds=30"
echo "    go tool pprof ${SOC}/debug/pprof/heap"
echo "═══════════════════════════════════════════════════"
echo "DONE"
