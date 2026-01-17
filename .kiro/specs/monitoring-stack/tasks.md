# Monitoring Stack — Tasks

## Phase 1: Docker Compose

- [x] **Task 1.1**: Создать `monitoring/docker-compose.yml`
  - Prometheus service
  - Grafana service
  - Alertmanager service

---

## Phase 2: Prometheus Config

- [x] **Task 2.1**: Создать `monitoring/prometheus/prometheus.yml`
  - Brain scrape job
  - Shield scrape job
  - Self-monitoring

- [x] **Task 2.2**: Создать alerting rules (`alerts.yml`)
  - HighRequestLatency
  - HighErrorRate
  - EngineDown
  - HighBlockRate
  - HighMemoryUsage
  - HighCacheMissRate

- [x] **Task 2.3**: Создать `alertmanager/alertmanager.yml`
  - Webhook receivers
  - Routing rules

---

## Phase 3: Grafana Dashboards

- [x] **Task 3.1**: Grafana provisioning
  - datasources/prometheus.yml
  - dashboards/dashboards.yml

- [x] **Task 3.2**: Brain Overview dashboard
  - Total Requests stat
  - Threats Detected stat
  - P95 Latency stat
  - Request Rate timeseries

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| docker-compose | 3 services | ✅ |
| Prometheus config | 4 scrape jobs | ✅ |
| Alerting rules | 6 rules | ✅ |
| Dashboard | Brain Overview | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
