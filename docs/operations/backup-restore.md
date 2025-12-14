# 💾 SENTINEL Backup & Disaster Recovery

> **Purpose:** Backup procedures, disaster recovery, business continuity  
> **RPO:** 1 hour (max data loss)  
> **RTO:** 15 minutes (max downtime)

---

## What to Back Up

| Component         | Data                         | Frequency | Method         |
| ----------------- | ---------------------------- | --------- | -------------- |
| **Redis**         | Cache, sessions, rate limits | Hourly    | RDB snapshot   |
| **Configuration** | .env, secrets, ConfigMaps    | On change | Git + Vault    |
| **Logs**          | Audit logs, analysis logs    | Daily     | S3/GCS archive |
| **Prometheus**    | Metrics history              | Daily     | Remote write   |

> **Note:** Brain and Gateway are **stateless** — no backup needed, just redeploy.

---

## Redis Backup

### Manual Backup

```bash
# Trigger RDB snapshot
redis-cli -a $REDIS_PASSWORD BGSAVE

# Wait for completion
redis-cli -a $REDIS_PASSWORD LASTSAVE

# Copy dump file
docker cp redis:/data/dump.rdb ./backups/redis-$(date +%Y%m%d-%H%M).rdb

# Or from Kubernetes
kubectl cp sentinel/redis-0:/data/dump.rdb ./backups/redis-$(date +%Y%m%d-%H%M).rdb
```

### Automated Backup (CronJob)

```yaml
# redis-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: redis-backup
  namespace: sentinel
spec:
  schedule: "0 * * * *" # Every hour
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: redis:7-alpine
              command:
                - /bin/sh
                - -c
                - |
                  redis-cli -h redis -a $REDIS_PASSWORD BGSAVE
                  sleep 10
                  aws s3 cp /data/dump.rdb s3://sentinel-backups/redis/$(date +%Y%m%d-%H%M).rdb
              env:
                - name: REDIS_PASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: sentinel-redis
                      key: password
          restartPolicy: OnFailure
```

### Redis Restore

```bash
# Stop Redis
kubectl scale statefulset redis --replicas=0

# Copy backup to PVC
kubectl cp ./backups/redis-20241214-1200.rdb sentinel/redis-pvc:/data/dump.rdb

# Start Redis
kubectl scale statefulset redis --replicas=1

# Verify
redis-cli -a $REDIS_PASSWORD DBSIZE
```

---

## Configuration Backup

### Secrets

```bash
# Export secrets (encrypted)
kubectl get secret sentinel-auth -o yaml > secrets/sentinel-auth.yaml
kubectl get secret sentinel-redis -o yaml > secrets/sentinel-redis.yaml

# Store in Vault (recommended)
vault kv put secret/sentinel/auth @secrets/sentinel-auth.json
```

### ConfigMaps

```bash
kubectl get configmap sentinel-config -o yaml > config/sentinel-config.yaml
```

### Environment Files

```bash
# Git-tracked (no secrets)
git add .env.example docker-compose.yml

# Secrets via Vault or encrypted storage
gpg --encrypt --recipient admin@company.com .env.production
```

---

## Log Archival

### Ship to S3/GCS

```yaml
# filebeat-config.yaml
output.s3:
  bucket: "sentinel-logs"
  region: "us-east-1"
  prefix: "sentinel/%{+yyyy.MM.dd}"
```

### Retention Policy

| Log Type    | Hot (local) | Warm (S3) | Cold (Glacier) |
| ----------- | ----------- | --------- | -------------- |
| Audit       | 7 days      | 90 days   | 7 years        |
| Application | 3 days      | 30 days   | 1 year         |
| Access      | 1 day       | 7 days    | 90 days        |

---

## Disaster Recovery

### Scenario 1: Single Pod Failure

**Impact:** Minimal (other replicas handle)  
**Recovery:** Automatic (Kubernetes restarts)

### Scenario 2: Zone Failure

**Impact:** Partial (pods in failed zone)  
**Recovery:**

```bash
# Scale up in healthy zones
kubectl scale deployment sentinel-brain --replicas=10

# Pods will schedule to available zones
```

### Scenario 3: Complete Cluster Loss

**Impact:** Total outage  
**Recovery:**

```bash
# 1. Deploy to new cluster
helm install sentinel sentinel/sentinel -f values.yaml

# 2. Restore Redis
kubectl cp ./backups/latest-redis.rdb redis:/data/dump.rdb

# 3. Restore secrets
kubectl apply -f secrets/

# 4. Update DNS
aws route53 change-resource-record-sets --hosted-zone-id Z123 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"sentinel.company.com","Type":"A","AliasTarget":{"DNSName":"new-lb.elb.amazonaws.com"}}}]}'
```

### Scenario 4: Ransomware/Compromise

**Impact:** Security incident  
**Recovery:**

1. **Isolate** — Cut network access
2. **Assess** — Determine scope
3. **Clean deploy** — New infrastructure from known-good images
4. **Restore** — From verified backups (scan first)
5. **Rotate** — All secrets, API keys
6. **Audit** — Post-incident review

---

## DR Testing

### Monthly DR Drill

1. **Backup Verification**

   ```bash
   # Restore to test environment
   redis-cli -h test-redis FLUSHALL
   redis-cli -h test-redis --rdb ./backups/latest.rdb
   redis-cli -h test-redis DBSIZE
   # Should match production
   ```

2. **Failover Test**

   ```bash
   # Kill primary brain pods
   kubectl delete pod -l app=sentinel-brain --grace-period=0

   # Verify traffic continues (via replicas)
   curl http://sentinel/health
   ```

3. **Full Restore Test** (Quarterly)
   - Spin up parallel environment
   - Restore all backups
   - Run integration tests
   - Document recovery time

---

## Backup Verification

### Automated Verification

```yaml
# backup-verify-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-verify
spec:
  schedule: "0 6 * * *" # Daily 6am
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: verify
              image: sentinel/backup-verify:latest
              command:
                - /bin/sh
                - -c
                - |
                  # Download latest backup
                  aws s3 cp s3://sentinel-backups/redis/latest.rdb /tmp/

                  # Load into test Redis
                  redis-cli -h test-redis FLUSHALL
                  redis-cli -h test-redis DEBUG RELOAD

                  # Verify
                  KEYS=$(redis-cli -h test-redis DBSIZE)
                  if [ "$KEYS" -lt 100 ]; then
                    echo "BACKUP VERIFICATION FAILED: Only $KEYS keys"
                    exit 1
                  fi

                  echo "Backup verified: $KEYS keys"
```

---

## Contacts

| Role           | Responsibility      | Contact        |
| -------------- | ------------------- | -------------- |
| Backup Owner   | Backup procedures   | platform-team@ |
| DR Coordinator | DR drills, planning | sre-lead@      |
| Security       | Incident response   | security@      |
