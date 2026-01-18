# ☸️ Урок 1.3: Kubernetes Deployment

> **Время: 30 минут** | Mid-Level Module 1

---

## Kubernetes Manifests

### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sentinel
  labels:
    app.kubernetes.io/name: sentinel
    app.kubernetes.io/part-of: ai-security
```

### Deployment

```yaml
# brain-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentinel-brain
  namespace: sentinel
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
        env:
        - name: SENTINEL_MODE
          value: "production"
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: sentinel-secrets
              key: redis-url
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service

```yaml
# brain-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: sentinel-brain
  namespace: sentinel
spec:
  selector:
    app: sentinel-brain
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sentinel-ingress
  namespace: sentinel
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
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
              number: 8080
```

### HorizontalPodAutoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sentinel-brain-hpa
  namespace: sentinel
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sentinel-brain
  minReplicas: 3
  maxReplicas: 10
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
```

---

## Helm Chart

```bash
# Install via Helm
helm repo add sentinel https://charts.sentinel.ai
helm install sentinel sentinel/sentinel \
  --namespace sentinel \
  --create-namespace \
  --set brain.replicas=3 \
  --set shield.enabled=true \
  --set redis.enabled=true
```

### values.yaml

```yaml
# values.yaml
global:
  imageRegistry: docker.io
  imagePullSecrets: []

brain:
  replicas: 3
  image:
    repository: sentinel/brain
    tag: v4.1
  resources:
    requests:
      memory: 2Gi
      cpu: 1
    limits:
      memory: 4Gi
      cpu: 2
  config:
    mode: production
    engines: all

shield:
  enabled: true
  replicas: 2
  image:
    repository: sentinel/shield
    tag: v4.1

redis:
  enabled: true
  architecture: replication
  replica:
    replicaCount: 2

postgresql:
  enabled: true
  architecture: replication
  replica:
    replicaCount: 1
```

---

## Deploy Commands

```bash
# Apply all manifests
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f brain-deployment.yaml
kubectl apply -f brain-service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

# Check status
kubectl get pods -n sentinel
kubectl get svc -n sentinel
kubectl get ingress -n sentinel

# Logs
kubectl logs -f deployment/sentinel-brain -n sentinel

# Scale manually
kubectl scale deployment sentinel-brain --replicas=5 -n sentinel
```

---

## Следующий урок

→ [1.4: High Availability](./04-high-availability.md)
