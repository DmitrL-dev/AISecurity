# SENTINEL Shield - Kubernetes Deployment

## Quick Start

```bash
# Create namespace
kubectl create namespace sentinel

# Apply all manifests
kubectl apply -f k8s/ -n sentinel

# Check status
kubectl get pods -n sentinel
kubectl get svc -n sentinel
```

## Files

| File | Description |
|------|-------------|
| `deployment.yaml` | Main deployment with 2 replicas, probes, security context |
| `service.yaml` | ClusterIP + LoadBalancer services |
| `configmap.yaml` | Configuration with shield.conf |
| `rbac.yaml` | ServiceAccount + Role + RoleBinding |
| `hpa.yaml` | Horizontal Pod Autoscaler (2-10 replicas) |

## Prerequisites

1. **TLS Secret** - Create before deployment:
```bash
kubectl create secret tls sentinel-shield-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n sentinel
```

2. **Brain Service** - Ensure sentinel-brain is deployed:
```bash
kubectl get svc sentinel-brain -n sentinel
```

## Features

- ✅ Security context (non-root, read-only filesystem)
- ✅ Resource limits (100m-500m CPU, 128Mi-512Mi memory)
- ✅ Liveness & Readiness probes
- ✅ Prometheus annotations for metrics scraping
- ✅ Pod anti-affinity for HA
- ✅ HPA for auto-scaling
- ✅ RBAC with minimal permissions

## Scaling

```bash
# Manual scale
kubectl scale deployment sentinel-shield --replicas=5 -n sentinel

# HPA will auto-scale based on CPU/memory
kubectl get hpa -n sentinel
```

## Monitoring

```bash
# View logs
kubectl logs -l app=sentinel-shield -n sentinel -f

# Port-forward metrics
kubectl port-forward svc/sentinel-shield 9090:9090 -n sentinel

# Access metrics
curl http://localhost:9090/metrics
```
