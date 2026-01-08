# Исследование и решения по дизайну

## Сводка
- **Функция**: `shield-audit-logging`
- **Объём исследования**: Расширение существующего компонента
- **Ключевые находки**:
  - SHIELD использует чистый C — логирование должно быть zero-copy для производительности
  - Существующая структура: `shield/src/utils/` — подходящее место для audit модуля
  - Ring buffer pattern оптимален для async logging без блокировок

## Лог исследований

### Производительность async logging
- **Контекст**: Требование <50μs latency на запрос
- **Источники**: Linux kernel ring buffer, LMAX Disruptor pattern
- **Находки**:
  - Single-producer/single-consumer lock-free ring buffer: O(1) insert
  - Memory-mapped file для persistence: минимальные syscalls
  - Batch flush: группировка записей снижает I/O overhead
- **Последствия**: Использовать SPSC ring buffer + mmap для append-only log

### Форматы compliance logging
- **Контекст**: Поддержка CEF, LEEF, syslog RFC 5424
- **Источники**: ArcSight CEF spec, IBM LEEF spec, RFC 5424
- **Находки**:
  - CEF: `CEF:0|SENTINEL|SHIELD|1.0|event_id|name|severity|...`
  - LEEF: IBM-specific, LEEF:1.0 header + tab-separated
  - RFC 5424: Structured data extension для custom fields
- **Последствия**: Pluggable formatter interface с compile-time selection

### Hash chain integrity
- **Контекст**: Неизменяемость логов для compliance
- **Источники**: Blockchain-style chaining, Certificate Transparency logs
- **Находки**:
  - SHA-256 chain: `hash_n = SHA256(hash_{n-1} || record_n)`
  - Periodic checkpoint: каждые N записей сохранять anchor hash
  - Verification: O(n) full scan или O(log n) с Merkle tree
- **Последствия**: Simple hash chain для append-only, checkpoint каждые 1000 записей

## Оценка архитектурных паттернов

| Вариант | Описание | Сильные стороны | Риски | Заметки |
|---------|----------|-----------------|-------|---------|
| Ring Buffer + File | SPSC queue → mmap file | Lock-free, zero-copy | Сложность recovery | **Выбрано** |
| Direct Write | sync write each event | Простота | Блокирует SHIELD | Неприемлемо |
| External Logger | syslog-ng/fluentd | Готовое решение | Зависимость | Для экспорта |

## Решения по дизайну

### Решение: Ring Buffer Architecture
- **Контекст**: Требование 10K evt/s + <50μs latency
- **Альтернативы**:
  1. Sync write — блокирует, неприемлемо
  2. Thread queue — lock contention
- **Выбранный подход**: Lock-free SPSC ring buffer с dedicated flush thread
- **Обоснование**: Proven pattern в high-performance systems (LMAX, Linux kernel)
- **Компромиссы**: Сложнее отладка, требует careful sizing
- **Follow-up**: Benchmark с реальной нагрузкой

### Решение: Pluggable Formatters
- **Контекст**: Множество форматов (JSONL, CEF, LEEF, syslog)
- **Выбранный подход**: Function pointer table с compile-time registration
- **Обоснование**: Zero runtime overhead, type-safe

## Риски и митигации
- **Потеря данных при crash** — fsync checkpoint каждые N записей
- **Buffer overflow** — backpressure с drop counter
- **Hash chain corruption** — periodic verification background thread

## Ссылки
- [RFC 5424 - Syslog Protocol](https://tools.ietf.org/html/rfc5424)
- [ArcSight CEF Format](https://docs.centrify.com/Content/IntegrationContent/SIEM/arcsight-cef/arcsight-cef-format.htm)
- [LMAX Disruptor](https://lmax-exchange.github.io/disruptor/)
