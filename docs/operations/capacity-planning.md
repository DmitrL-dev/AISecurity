# 📈 SENTINEL Capacity Planning Guide

> **Purpose:** Resource sizing, scaling guidelines, cost estimation  
> **Review Frequency:** Monthly

---

## Quick Sizing Guide

| Tier           | Requests/sec | Gateway     | Brain             | Redis   | Est. Cost  |
| -------------- | ------------ | ----------- | ----------------- | ------- | ---------- |
| **Dev**        | 1-10         | 1x 2CPU/2GB | 1x 4CPU/8GB       | 1x 2GB  | ~$100/mo   |
| **Startup**    | 10-100       | 2x 2CPU/4GB | 3x 4CPU/16GB      | 3x 4GB  | ~$500/mo   |
| **Growth**     | 100-1000     | 3x 4CPU/8GB | 5x 8CPU/32GB      | 3x 8GB  | ~$2000/mo  |
| **Enterprise** | 1000+        | 5x 4CPU/8GB | 10x 8CPU/32GB+GPU | Cluster | ~$5000+/mo |

---

## Component Sizing

### Gateway

**Rule of thumb:** 1 Gateway handles ~500 req/sec

| Metric      | Per Gateway       |
| ----------- | ----------------- |
| CPU         | 2-4 cores         |
| Memory      | 2-4 GB            |
| Network     | 1 Gbps            |
| Connections | 10,000 concurrent |

**Scaling trigger:** CPU > 70% sustained

### Brain

**Rule of thumb:** 1 Brain handles ~50 req/sec (balanced mode)

| Mode       | Req/sec per Brain | Latency |
| ---------- | ----------------- | ------- |
| `fast`     | 200               | ~10ms   |
| `balanced` | 50                | ~50ms   |
| `thorough` | 10                | ~200ms  |

| Metric         | Per Brain      |
| -------------- | -------------- |
| CPU            | 4-8 cores      |
| Memory         | 16-32 GB       |
| GPU (optional) | 1x NVIDIA 8GB+ |

**Scaling trigger:** CPU > 70% OR p95 latency > 100ms

### Redis

**Rule of thumb:** 1GB per 100,000 cached analyses

| Metric      | Recommendation |
| ----------- | -------------- |
| Memory      | 4-16 GB        |
| Connections | 1000 max       |
| Persistence | AOF + RDB      |

**Scaling trigger:** Memory > 80% OR connections > 800

---

## Capacity Formulas

### Gateway Count

```
gateway_count = ceil(peak_rps / 500) + 1  # +1 for redundancy
```

Example: 800 req/sec → `ceil(800/500) + 1 = 3` Gateways

### Brain Count

```
brain_count = ceil(peak_rps / throughput_per_brain) + buffer

Where:
  throughput_per_brain =
    fast: 200
    balanced: 50
    thorough: 10
  buffer = 20% for headroom
```

Example: 300 req/sec, balanced mode:

```
brain_count = ceil(300/50) * 1.2 = ceil(6 * 1.2) = 8 Brains
```

### Redis Memory

```
redis_memory_gb = (cache_entries * avg_entry_size_kb) / 1024 / 1024

Where:
  cache_entries = unique_prompts_per_day * cache_ttl_days
  avg_entry_size_kb ≈ 2
```

---

## Traffic Patterns

### Daily Pattern

```
            ▲ Requests
       500  │          ╭───────╮
            │         ╱         ╲
       250  │        ╱           ╲
            │    ╭──╯             ╰──╮
         0  ├────┴────┬────┬────┬────┴────▶ Time
            0    6   12   18   24

Peak: 12:00-16:00 (business hours)
Trough: 02:00-06:00 (overnight)
```

### Scaling Strategy

| Time     | Load  | Strategy                   |
| -------- | ----- | -------------------------- |
| Off-peak | 20%   | Scale down to min replicas |
| Normal   | 60%   | Maintain baseline          |
| Peak     | 100%  | Scale to max or autoscale  |
| Burst    | 150%+ | Rate limit + queue         |

---

## Autoscaling Configuration

### Kubernetes HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentinel-brain-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentinel-brain
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 25
          periodSeconds: 60
```

---

## Cost Optimization

### Right-sizing Tips

1. **Use `fast` mode** for high-volume, low-risk traffic
2. **Disable unused engines** (`DISABLED_ENGINES=...`)
3. **Increase cache TTL** for repetitive queries
4. **Use spot/preemptible instances** for Brain (stateless)

### Cost Breakdown (typical)

| Component           | % of Cost |
| ------------------- | --------- |
| Brain compute       | 60%       |
| Brain GPU (if used) | 20%       |
| Gateway compute     | 10%       |
| Redis               | 5%        |
| Storage/Network     | 5%        |

### Saving Strategies

| Strategy                 | Savings     | Risk               |
| ------------------------ | ----------- | ------------------ |
| Spot instances for Brain | 60-70%      | Pod eviction       |
| Reserved instances       | 30-40%      | Commitment         |
| Scale to zero overnight  | 30%         | Cold start latency |
| Use `fast` mode          | 75% compute | Less security      |

---

## Capacity Review Checklist

### Monthly Review

- [ ] Current utilization vs provisioned
- [ ] Traffic growth trend
- [ ] Cost per request trend
- [ ] Incidents caused by capacity
- [ ] Upcoming traffic events (launches, campaigns)

### Quarterly Planning

- [ ] 3-month traffic forecast
- [ ] Budget alignment
- [ ] Infrastructure upgrades needed
- [ ] Reserved instance purchases
