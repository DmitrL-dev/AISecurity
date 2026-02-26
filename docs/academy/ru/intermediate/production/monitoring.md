# 📊 Урок 2.4: Мониторинг и Observability

> **Время: 35 минут** | Mid-Level Модуль 2

---

## Три столпа

| Столп | Инструмент | Назначение |
|-------|------------|------------|
| **Метрики** | Prometheus | Числовые данные |
| **Логи** | ELK/Loki | Записи событий |
| **Трейсы** | Jaeger/Tempo | Поток запросов |

---

## Prometheus Метрики

```rust
use prometheus::{Counter, Histogram, CounterVec, HistogramVec, opts, register_counter_vec, register_histogram_vec};
use lazy_static::lazy_static;

lazy_static! {
    // Определяем метрики
    static ref SCANS_TOTAL: CounterVec = register_counter_vec!(
        opts!("sentinel_scans_total", "Всего выполнено сканирований"),
        &["engine", "result"]
    ).unwrap();

    static ref SCAN_DURATION: HistogramVec = register_histogram_vec!(
        "sentinel_scan_duration_seconds",
        "Длительность сканирования в секундах",
        &["engine"]
    ).unwrap();
}

// Использование в коде
fn scan(text: &str) -> ScanResult {
    let timer = SCAN_DURATION.with_label_values(&["injection"]).start_timer();
    let result = detector.scan(text);
    timer.observe_duration();

    SCANS_TOTAL.with_label_values(&[
        "injection",
        if result.is_threat { "threat" } else { "safe" },
    ]).inc();

    result
}

// Экспорт метрик
// prometheus::default_registry() на порту 9090
```

---

## Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Сканирований в секунду",
      "type": "graph",
      "targets": [{
        "expr": "rate(sentinel_scans_total[5m])"
      }]
    },
    {
      "title": "Процент угроз",
      "type": "stat",
      "targets": [{
        "expr": "sum(rate(sentinel_scans_total{result='threat'}[1h])) / sum(rate(sentinel_scans_total[1h]))"
      }]
    }
  ]
}
```

---

## Структурированное логирование

```rust
use tracing::{info, instrument};

#[instrument(skip(text), fields(text_length = text.len()))]
fn scan_with_logging(text: &str) -> ScanResult {
    let request_id = generate_id();
    info!(request_id = %request_id, "scan_started");

    let result = detector.scan(text);

    info!(
        request_id = %request_id,
        is_threat = result.is_threat,
        confidence = result.confidence,
        duration_ms = result.duration * 1000.0,
        "scan_completed"
    );

    result
}
```

---

## OpenTelemetry Трейсинг

```rust
use opentelemetry::trace::{Tracer, SpanKind};
use opentelemetry::global;

fn scan_with_tracing(text: &str) -> ScanResult {
    let tracer = global::tracer("sentinel");

    tracer.in_span("sentinel.scan", |cx| {
        let span = cx.span();
        span.set_attribute("text.length".into(), (text.len() as i64).into());

        let tier1_result = tracer.in_span("tier1.scan", |_| {
            tier1_scan(text)
        });

        let tier2_result = tracer.in_span("tier2.scan", |_| {
            tier2_scan(text)
        });

        span.set_attribute("result.is_threat".into(), result.is_threat.into());
        result
    })
}
```

---

## Правила алертинга

```yaml
# prometheus/alerts.yml
groups:
  - name: sentinel
    rules:
      - alert: HighThreatRate
        expr: rate(sentinel_scans_total{result="threat"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Высокий процент обнаружения угроз"
          
      - alert: ScanLatencyHigh
        expr: histogram_quantile(0.99, sentinel_scan_duration_seconds) > 0.5
        for: 5m
        labels:
          severity: critical
```

---

## Ключевые выводы

1. **Три столпа** — метрики, логи, трейсы
2. **Prometheus** — для числовых метрик
3. **Структурированное логирование** — для поиска событий
4. **OpenTelemetry** — для распределённого трейсинга
5. **Алертинг** — проактивное реагирование

---

## Следующий урок

→ [3.1: Кастомные движки](./09-custom-engines.md)
