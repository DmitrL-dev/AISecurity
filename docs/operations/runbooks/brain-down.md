# 🔥 Runbook: Brain Service Down

> **Severity:** P1 Critical  
> **Response Time:** 5 minutes  
> **Alert:** `SentinelBrainDown`

---

## Symptoms

- Alert: `SentinelBrainDown` firing
- Error logs: `connection refused to brain:50051`
- API returns: `503 Service Unavailable`
- Block/allow decisions failing

---

## Impact

**CRITICAL:** All LLM requests are NOT being analyzed. Security protection is OFFLINE.

**Options:**

1. Block all traffic (safe but disrupts service)
2. Allow all traffic (risky but maintains availability)
3. Fix Brain immediately (preferred)

---

## Diagnosis

### Step 1: Check Brain Pod Status

```bash
# Kubernetes
kubectl get pods -l app=sentinel-brain -n sentinel
kubectl describe pod <brain-pod-name> -n sentinel

# Docker Compose
docker compose ps brain
docker compose logs brain --tail=100
```

### Step 2: Check Brain Health Endpoint

```bash
# Direct health check
curl http://brain:50051/health

# gRPC health check
grpcurl -plaintext brain:50051 grpc.health.v1.Health/Check
```

### Step 3: Check Resources

```bash
# CPU/Memory
kubectl top pod -l app=sentinel-brain -n sentinel

# Disk space
kubectl exec <brain-pod> -- df -h
```

### Step 4: Check Dependencies

```bash
# Redis connectivity from Brain
kubectl exec <brain-pod> -- redis-cli -h redis ping

# Network to Brain
kubectl exec <gateway-pod> -- nc -zv brain 50051
```

---

## Common Causes & Fixes

### Cause 1: OOM Killed

**Symptoms:**

```
State: Terminated
Reason: OOMKilled
```

**Fix:**

```bash
# Increase memory limit
kubectl patch deployment sentinel-brain -n sentinel -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"brain","resources":{"limits":{"memory":"16Gi"}}}]}}}}'
```

### Cause 2: CrashLoopBackOff

**Symptoms:**

```
Status: CrashLoopBackOff
```

**Diagnosis:**

```bash
kubectl logs <brain-pod> --previous
```

**Fix:** Usually a configuration error or missing dependency. Roll back:

```bash
kubectl rollout undo deployment sentinel-brain -n sentinel
```

### Cause 3: Image Pull Error

**Symptoms:**

```
Failed to pull image
```

**Fix:**

```bash
# Check image exists
docker pull ghcr.io/your-org/sentinel-brain:1.0.0

# Check imagePullSecrets
kubectl get secrets -n sentinel
```

### Cause 4: Redis Down

**Symptoms:**

```
ConnectionError: Error 111 connecting to redis:6379
```

**Fix:**

```bash
# Restart Redis
kubectl rollout restart statefulset sentinel-redis -n sentinel

# Or bypass Redis temporarily
kubectl set env deployment/sentinel-brain REDIS_ENABLED=false
```

---

## Recovery Steps

### Quick Restart

```bash
# Kubernetes
kubectl rollout restart deployment sentinel-brain -n sentinel

# Docker Compose
docker compose restart brain
```

### Scale Up (if replicas down)

```bash
kubectl scale deployment sentinel-brain --replicas=5 -n sentinel
```

### Rollback (if recent deployment)

```bash
kubectl rollout undo deployment sentinel-brain -n sentinel
```

---

## Verification

After fix, verify:

```bash
# 1. Pods running
kubectl get pods -l app=sentinel-brain -n sentinel
# All should be Running

# 2. Health check
curl http://localhost:8080/health
# {"status": "healthy", "components": {"brain": "healthy"}}

# 3. Test analysis
curl -X POST http://localhost:8080/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'
# Should return risk_score
```

---

## Escalation

If not resolved in 15 minutes:

1. Page Platform Lead
2. Consider fallback mode (allow-all or block-all)
3. Engage vendor support if applicable
