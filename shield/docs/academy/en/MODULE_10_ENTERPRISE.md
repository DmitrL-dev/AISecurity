# SENTINEL Academy — Module 10

## Enterprise Deployment

_SSP Level | Duration: 4 hours_

---

## Docker

```dockerfile
FROM sentinel/shield:latest
COPY config.json /etc/shield/
EXPOSE 8080 9090
CMD ["shield", "-c", "/etc/shield/config.json"]
```

```bash
docker build -t myshield .
docker run -d -p 8080:8080 myshield
```

---

## Kubernetes

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shield
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: shield
        image: sentinel/shield:1.2.0
        ports:
        - containerPort: 8080
        - containerPort: 9090
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: shield
spec:
  selector:
    app: shield
  ports:
  - port: 8080
    targetPort: 8080
```

---

## Sidecar Pattern

```yaml
spec:
  containers:
  - name: app
    image: your-app
  - name: shield
    image: sentinel/shield
    ports:
    - containerPort: 8080
```

---

## Capacity Planning

| Metric | Per Core |
|--------|----------|
| Requests | 10K/sec |
| Memory | 50MB base |
| Latency | < 1ms |

---

_"Enterprise needs enterprise architecture."_
