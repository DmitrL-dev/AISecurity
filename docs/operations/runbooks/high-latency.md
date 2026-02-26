# 🐢 Runbook: High Latency

> **Severity:** P2 Warning  
> **Response Time:** 1 hour  
> **Alert:** `SentinelHighLatency`

---

## Symptoms

- Alert: `SentinelHighLatency` (p95 > 500ms)
- Slow API responses
- Timeouts in client applications
- Queue buildup

---

## Impact

**Moderate:** Requests are succeeding but slowly. May cause:

- User-facing delays
- Timeout errors in callers
- Cascading failures if callers retry

---

## Diagnosis

### Step 1: Identify Bottleneck

```promql
# Check which component is slow
histogram_quantile(0.95, rate(sentinel_gateway_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(sentinel_analysis_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(sentinel_engine_duration_seconds_bucket[5m]))
```

### Step 2: Check Engine Performance

```promql
# Slowest engines
topk(5, histogram_quantile(0.95,
  rate(sentinel_engine_duration_seconds_bucket[5m])
) by (engine))
```

### Step 3: Check Resource Utilization

```bash
# CPU/Memory
kubectl top pod -l app=sentinel-brain -n sentinel

# Check for throttling
kubectl describe pod <brain-pod> | grep -A5 "Limits"
```

### Step 4: Check External Dependencies

```bash
# Redis latency
redis-cli --latency -h redis

# Network latency
kubectl exec <gateway-pod> -- ping -c 5 brain
```

---

## Common Causes & Fixes

### Cause 1: Heavy Engines Overloaded

**Symptoms:** TDA, Sheaf, or ML engines slow

**Quick Fix:**

```bash
# Disable heavy engines temporarily
kubectl set env deployment/sentinel-brain \
  DISABLED_ENGINES="tda_enhanced,sheaf_coherence,qwen_guard"
```

**Long-term:** Add more Brain replicas or switch to `fast` mode.

### Cause 2: CPU Throttling

**Symptoms:** CPU at limit, high throttle_time

**Fix:**

```bash
kubectl patch deployment sentinel-brain -n sentinel -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"brain","resources":{"limits":{"cpu":"4"}}}]}}}}'
```

### Cause 3: Redis Slow

**Symptoms:** `redis-cli --latency` shows >10ms

**Fix:**

```bash
# Check Redis memory
redis-cli info memory

# If full, increase maxmemory or flush cache
redis-cli FLUSHDB
```

### Cause 4: Too Much Traffic

**Symptoms:** Request rate spike

**Fix:**

```bash
# Scale up
kubectl scale deployment sentinel-brain --replicas=10 -n sentinel

# Or enable more aggressive rate limiting
kubectl set env deployment/sentinel-gateway RATE_LIMIT_REQUESTS=50
```

### Cause 5: Analysis Mode Too Thorough

**Symptoms:** All engines running, `balanced` or `thorough` mode

**Fix:**

```bash
# Switch to fast mode temporarily
kubectl set env deployment/sentinel-brain BRAIN_ANALYSIS_MODE=fast
```

---

## Quick Mitigation

### Option A: Switch to Fast Mode

```bash
kubectl set env deployment/sentinel-brain BRAIN_ANALYSIS_MODE=fast
# p95: 200ms → 20ms
# But: Fewer engines, less security
```

### Option B: Scale Up

```bash
kubectl scale deployment sentinel-brain --replicas=10
# Wait 2-3 min for pods to be ready
```

### Option C: Disable Heavy Engines

```bash
kubectl set env deployment/sentinel-brain \
  DISABLED_ENGINES="tda_enhanced,sheaf_coherence,hyperbolic_geometry"
```

---

## Verification

```bash
# Check p95 is below threshold
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, rate(sentinel_analysis_duration_seconds_bucket[5m]))'
# Should be < 0.5 (500ms)

# Test response time
time curl -X POST http://localhost:8080/v1/analyze \
  -d '{"text": "test"}'
# Should complete in <100ms
```

---

## Escalation

If latency persists after 1 hour:

1. Notify Platform Lead
2. Consider switching to fast mode permanently until capacity increased
3. Schedule capacity review
