# ☸️ Lesson 1.3: Kubernetes

> **Time: 45 minutes** | Mid-Level Module 1

---

## Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-brain
  labels:
    app: sentinel
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sentinel-brain
  template:
    metadata:
      labels:
        app: sentinel-brain
    spec:
      containers:
      - name: brain
        image: sentinel/brain:v4.1
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          periodSeconds: 10
```

---

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sentinel-brain
spec:
  selector:
    app: sentinel-brain
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

---

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sentinel-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - sentinel.example.com
    secretName: sentinel-tls
  rules:
  - host: sentinel.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: sentinel-brain
            port:
              number: 80
```

---

## Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentinel-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentinel-brain
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Helm Chart

```bash
helm repo add sentinel https://charts.sentinel.ai
helm install sentinel sentinel/brain \
  --set replicas=3 \
  --set ingress.enabled=true \
  --set ingress.host=sentinel.example.com
```

---

## Next Lesson

→ [1.4: High Availability](./04-high-availability.md)
