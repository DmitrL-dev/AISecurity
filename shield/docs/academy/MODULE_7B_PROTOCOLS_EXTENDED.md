# SENTINEL Academy — Module 7B

## Расширенные Протоколы Shield

_SSP Level | Время: 4 часа_

---

## Введение

В дополнение к 6 базовым протоколам (Module 7), Shield имеет **14 дополнительных протоколов** для enterprise функций:

| Категория       | Протоколы         |
| --------------- | ----------------- |
| **Discovery**   | ZRP, ZHP          |
| **Traffic**     | SPP, SQP, SRP     |
| **Analytics**   | STT, SEM, SLA     |
| **HA**          | SMRP              |
| **Integration** | SGP, SIEM         |
| **Security**    | STLS, SZAA, SSigP |

---

## 7B.1 ZRP — Zone Registration Protocol

### Назначение

Регистрация и управление зонами в кластере Shield.

### Операции

| Тип              | Описание               |
| ---------------- | ---------------------- |
| `ZRP_REGISTER`   | Регистрация новой зоны |
| `ZRP_DEREGISTER` | Удаление зоны          |
| `ZRP_UPDATE`     | Обновление метаданных  |
| `ZRP_LIST`       | Список всех зон        |

### C API

```c
#include "protocols/zrp.h"

zrp_context_t *ctx;
zrp_init(&ctx, "shield-node-1");

// Регистрация зоны
zrp_zone_info_t info = {
    .name = "llm-openai",
    .type = ZONE_TYPE_LLM,
    .provider = "openai",
    .trust_level = 7
};
zrp_register(ctx, &info);

// Получить список
zrp_zone_list_t list;
zrp_list(ctx, &list);

zrp_destroy(ctx);
```

---

## 7B.2 ZHP — Zone Health Protocol

### Назначение

Мониторинг состояния зон и алертинг.

### Health Checks

- Response time
- Error rate
- Connection pool
- Queue depth

### C API

```c
#include "protocols/zhp.h"

zhp_context_t *ctx;
zhp_init(&ctx);

// Проверка здоровья зоны
zhp_health_t health;
zhp_check(ctx, "llm-zone", &health);

printf("Status: %s, Latency: %dms\n",
       health.healthy ? "HEALTHY" : "DEGRADED",
       health.latency_ms);

// Подписка на алерты
zhp_subscribe(ctx, on_health_alert);
```

---

## 7B.3 SPP — Shield Policy Protocol

### Назначение

Распространение политик безопасности по кластеру.

### Операции

| Тип        | Описание             |
| ---------- | -------------------- |
| `SPP_PUSH` | Отправить политику   |
| `SPP_PULL` | Запросить политику   |
| `SPP_SYNC` | Синхронизировать все |
| `SPP_DIFF` | Получить разницу     |

### C API

```c
#include "protocols/spp.h"

spp_context_t *ctx;
spp_init(&ctx);

// Push политики
spp_policy_t policy = {
    .name = "block-injection",
    .version = 2,
    .rules_json = "..."
};
spp_push(ctx, "all-nodes", &policy);

// Sync кластера
spp_sync(ctx);
```

---

## 7B.4 SQP — Shield Quarantine Protocol

### Назначение

Управление карантином подозрительных запросов.

### Операции

```c
#include "protocols/sqp.h"

sqp_context_t *ctx;
sqp_init(&ctx);

// Поместить в карантин
sqp_quarantine(ctx, request_id, "Suspected injection", 3600);

// Получить из карантина
sqp_entry_t entry;
sqp_get(ctx, request_id, &entry);

// Анализ
sqp_analyze(ctx, request_id, &analysis_result);

// Освободить или удалить
sqp_release(ctx, request_id);
sqp_delete(ctx, request_id);
```

---

## 7B.5 SRP — Shield Redirect Protocol

### Назначение

Перенаправление и зеркалирование трафика.

### Use Cases

- Redirect на honeypot
- Mirror для анализа
- A/B testing
- Canary deployment

### C API

```c
#include "protocols/srp.h"

srp_context_t *ctx;
srp_init(&ctx);

// Redirect правило
srp_rule_t rule = {
    .match_pattern = "attack-*",
    .action = SRP_ACTION_REDIRECT,
    .target = "honeypot-zone"
};
srp_add_rule(ctx, &rule);

// Mirror трафика
srp_mirror(ctx, "production", "analysis", 0.1);  // 10% traffic
```

---

## 7B.6 STT — Shield Threat Telemetry

### Назначение

Сбор и отправка threat intelligence данных.

### Типы событий

| Тип               | Описание                |
| ----------------- | ----------------------- |
| `THREAT_DETECTED` | Обнаружена угроза       |
| `IOC_OBSERVED`    | Индикатор компрометации |
| `ATTACK_PATTERN`  | Паттерн атаки           |
| `ANOMALY`         | Аномальное поведение    |

### C API

```c
#include "protocols/stt.h"

stt_context_t *ctx;
stt_init(&ctx, "https://intel.sentinel.io");

// Отправить событие
stt_threat_t threat = {
    .type = THREAT_TYPE_INJECTION,
    .severity = SEVERITY_HIGH,
    .source_ip = "192.168.1.100",
    .payload_hash = "abc123..."
};
stt_report(ctx, &threat);

// Получить IOC
stt_ioc_t iocs[100];
size_t count;
stt_get_iocs(ctx, iocs, 100, &count);
```

---

## 7B.7 SEM — Shield Event Manager

### Назначение

Централизованное управление событиями и корреляция.

### Функции

- Event queue
- Correlation engine
- Alert aggregation
- Event enrichment

### C API

```c
#include "protocols/sem.h"

sem_context_t *ctx;
sem_init(&ctx);

// Отправить событие
sem_event_t event = {
    .type = SEM_EVENT_SECURITY,
    .severity = 8,
    .message = "Jailbreak attempt detected",
    .zone = "external",
    .session_id = "sess123"
};
sem_send(ctx, &event);

// Запрос событий
sem_query_t query = {
    .time_from = time(NULL) - 3600,
    .severity_min = 7
};
sem_query(ctx, &query, events, &count);

// Корреляция
sem_correlate(ctx, "injection-pattern", &correlated);
```

---

## 7B.8 SLA — Shield Level Agreement

### Назначение

Мониторинг SLA и генерация отчетов.

### Метрики SLA

| Метрика      | Target  |
| ------------ | ------- |
| Latency P99  | < 100ms |
| Availability | 99.9%   |
| Error Rate   | < 0.1%  |
| Throughput   | > 10K/s |

### C API

```c
#include "protocols/sla.h"

sla_context_t *ctx;
sla_init(&ctx);

// Определить SLA
sla_define(ctx, "premium", SLA_LATENCY_P99, 50, SLA_UNIT_MS);
sla_define(ctx, "premium", SLA_AVAILABILITY, 99.99, SLA_UNIT_PERCENT);

// Проверить
sla_report_t report;
sla_check(ctx, "premium", &report);

printf("SLA compliance: %.1f%%\n", report.compliance_percent);
```

---

## 7B.9 SMRP — Shield Multicast Replication

### Назначение

Multicast распространение сигнатур по кластеру.

### Преимущества над unicast

- Efficient bandwidth
- Real-time updates
- Reduced latency
- Scalable to 100+ nodes

### C API

```c
#include "protocols/smrp.h"

smrp_context_t *ctx;
smrp_init(&ctx, "239.255.1.1", 5005);

// Присоединиться к группе
smrp_join(ctx, "signatures");

// Публикация сигнатуры
smrp_signature_t sig = {
    .id = "SIG-2026-001",
    .pattern = "ignore\\s+previous",
    .category = "injection"
};
smrp_publish(ctx, "signatures", &sig);

// Получение
smrp_receive(ctx, on_signature_received, NULL);
```

---

## 7B.10 SGP — Shield-Gateway Protocol

### Назначение

Коммуникация между Shield и API Gateway.

### Операции

| Тип            | Описание            |
| -------------- | ------------------- |
| `SGP_REGISTER` | Регистрация gateway |
| `SGP_CONFIG`   | Конфигурация        |
| `SGP_HEALTH`   | Health check        |
| `SGP_ROUTE`    | Routing update      |

### C API

```c
#include "protocols/sgp.h"

sgp_context_t *ctx;
sgp_init(&ctx, "gateway-1");

// Подключиться к gateway
sgp_connect(ctx, "api-gateway.internal:8080");

// Зарегистрировать route
sgp_route_t route = {
    .path = "/v1/chat",
    .zone = "llm-zone",
    .policy = "default"
};
sgp_add_route(ctx, &route);

// Sync конфигурации
sgp_sync_config(ctx);
```

---

## 7B.11 SIEM — Security Information Export

### Назначение

Экспорт событий в SIEM системы.

### Форматы

| Формат   | Описание                  |
| -------- | ------------------------- |
| `CEF`    | Common Event Format       |
| `JSON`   | Structured JSON           |
| `SYSLOG` | RFC 5424                  |
| `LEEF`   | Log Event Extended Format |

### C API

```c
#include "protocols/siem.h"

siem_context_t *ctx;
siem_init(&ctx, SIEM_FORMAT_CEF);
siem_set_destination(ctx, "splunk.company.com", 514);

// Отправить событие
siem_event_t event = {
    .severity = 8,
    .category = "ai-security",
    .action = "block",
    .outcome = "success",
    .source = "shield-node-1"
};
siem_send(ctx, &event);

// Batch отправка
siem_flush(ctx);
```

---

## 7B.12 STLS — Shield TLS Protocol

### Назначение

Mutual TLS для безопасной коммуникации.

### Особенности

- mTLS authentication
- Certificate rotation
- CRL checking
- OCSP stapling

### C API

```c
#include "protocols/stls.h"

stls_context_t *ctx;
stls_init(&ctx);

// Загрузить сертификаты
stls_load_cert(ctx, "/etc/shield/cert.pem");
stls_load_key(ctx, "/etc/shield/key.pem");
stls_load_ca(ctx, "/etc/shield/ca.pem");

// Установить соединение
stls_conn_t *conn;
stls_connect(ctx, "peer.internal:5006", &conn);

// Проверить peer
stls_peer_info_t peer;
stls_get_peer_info(conn, &peer);
printf("Peer CN: %s\n", peer.common_name);
```

---

## 7B.13 SZAA — Shield Zero-Trust Auth

### Назначение

Zero-trust аутентификация для всех компонентов.

### Методы аутентификации

| Метод   | Use Case            |
| ------- | ------------------- |
| `TOKEN` | API keys            |
| `CERT`  | mTLS                |
| `JWT`   | Service-to-service  |
| `OIDC`  | User authentication |

### C API

```c
#include "protocols/szaa.h"

szaa_context_t *ctx;
szaa_init(&ctx, SZAA_MODE_STRICT);

// Аутентификация по токену
szaa_result_t result;
szaa_authenticate(ctx, SZAA_METHOD_TOKEN,
                  "secret-api-key", &result);

if (result.authenticated) {
    printf("Identity: %s, Roles: %s\n",
           result.identity, result.roles);
}

// Проверка авторизации
bool allowed = szaa_authorize(ctx, &result, "admin", "write");
```

---

## 7B.14 SSigP — Shield Signature Protocol

### Назначение

Управление и распространение сигнатур угроз.

### Операции

| Тип               | Описание          |
| ----------------- | ----------------- |
| `SSIGP_UPDATE`    | Обновить БД       |
| `SSIGP_SUBSCRIBE` | Подписаться       |
| `SSIGP_QUERY`     | Запрос сигнатуры  |
| `SSIGP_VERIFY`    | Проверить подпись |

### C API

```c
#include "protocols/ssigp.h"

ssigp_context_t *ctx;
ssigp_init(&ctx, "https://signatures.sentinel.io");

// Обновить базу
ssigp_update_result_t result;
ssigp_update(ctx, &result);
printf("Updated: %d new, %d modified\n",
       result.new_count, result.modified_count);

// Подписка на real-time
ssigp_subscribe(ctx, on_new_signature, NULL);

// Проверить паттерн
ssigp_match_t matches[100];
size_t count;
ssigp_check(ctx, input, input_len, matches, 100, &count);
```

---

## Сводная таблица всех 20 протоколов

| #   | Протокол | Категория   | Назначение           |
| --- | -------- | ----------- | -------------------- |
| 1   | STP      | Traffic     | Передача данных      |
| 2   | SBP      | Integration | Shield-Brain связь   |
| 3   | ZDP      | Discovery   | Обнаружение зон      |
| 4   | SHSP     | HA          | Hot Standby          |
| 5   | SAF      | Analytics   | Метрики streaming    |
| 6   | SSRP     | HA          | State replication    |
| 7   | ZRP      | Discovery   | Регистрация зон      |
| 8   | ZHP      | Discovery   | Health зон           |
| 9   | SPP      | Traffic     | Политики             |
| 10  | SQP      | Traffic     | Карантин             |
| 11  | SRP      | Traffic     | Redirect             |
| 12  | STT      | Analytics   | Threat telemetry     |
| 13  | SEM      | Analytics   | Event manager        |
| 14  | SLA      | Analytics   | SLA monitoring       |
| 15  | SMRP     | HA          | Multicast signatures |
| 16  | SGP      | Integration | Gateway protocol     |
| 17  | SIEM     | Integration | SIEM export          |
| 18  | STLS     | Security    | Mutual TLS           |
| 19  | SZAA     | Security    | Zero-trust auth      |
| 20  | SSigP    | Security    | Signature updates    |

---

## Практика

### Задание 1: Policy Distribution

Настрой SPP для синхронизации политик:

- Push политики на 3 узла
- Проверь версии
- Выполни diff

### Задание 2: SIEM Integration

Настрой экспорт в Splunk:

- Формат CEF
- Минимальный severity: 5
- Batch size: 100

### Задание 3: Zero-Trust

Реализуй SZAA flow:

- Аутентификация по JWT
- Проверка ролей
- Audit logging

---

## Итоги Module 7B

- **20 протоколов** для enterprise Shield
- Полное покрытие: Discovery, Traffic, Analytics, HA, Integration, Security
- C API для каждого протокола
- Production-ready архитектура

---

_"20 протоколов = полная enterprise платформа."_
