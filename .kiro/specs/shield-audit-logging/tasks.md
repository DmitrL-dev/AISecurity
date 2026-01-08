# План реализации

## Обзор
**Функция**: shield-audit-logging  
**Требования покрыты**: 1-6 (все 6 требований)  
**Оценка**: 8 основных задач, 18 подзадач

---

## Задачи

- [ ] 1. Создать структуру модуля audit
  - [ ] 1.1 Создать каталог `shield/src/audit/` с Makefile
    - Добавить audit.h, audit.c, ring_buffer.h, ring_buffer.c
    - Интегрировать в основной Makefile SHIELD
    - _Требования: 1.1_
  - [ ] 1.2 Определить структуры AuditConfig и AuditEvent
    - Типы полей согласно design.md
    - _Требования: 1.1, 1.2, 1.3_

- [ ] 2. Реализовать lock-free ring buffer (P)
  - [ ] 2.1 Реализовать SPSC ring buffer с atomics
    - rb_init(), rb_push(), rb_pop_batch(), rb_destroy()
    - Memory ordering: acquire/release semantics
    - _Требования: 6.1, 6.2_
  - [ ] 2.2 Добавить backpressure механизм
    - Drop oldest при переполнении
    - Инкремент dropped_events counter
    - _Требования: 6.3_

- [ ] 3. Реализовать hash chain integrity (P)
  - [ ] 3.1 Реализовать SHA-256 chain functions
    - hc_init(), hc_append(), hc_verify()
    - Использовать OpenSSL EVP API
    - _Требования: 3.1, 3.2_
  - [ ] 3.2 Добавить checkpoint механизм
    - Сохранять anchor hash каждые 1000 записей
    - _Требования: 3.4_

- [ ] 4. Реализовать форматтеры логов (P)
  - [ ] 4.1 Реализовать format_jsonl()
    - JSON Lines формат с escape
    - _Требования: 2.1, 2.2_
  - [ ] 4.2 Реализовать format_cef()
    - ArcSight CEF:0 формат
    - _Требования: 2.3_
  - [ ] 4.3 Реализовать format_syslog()
    - RFC 5424 structured data
    - _Требования: 2.4_

- [ ] 5. Реализовать file writer с ротацией
  - [ ] 5.1 Реализовать mmap-based append writer
    - Open, mmap, append, fsync
    - _Требования: 1.4, 6.2_
  - [ ] 5.2 Реализовать size-based ротацию
    - Ротация при достижении max_size (100MB default)
    - gzip compression архивов
    - _Требования: 4.1, 4.2, 4.3_
  - [ ] 5.3 Реализовать retention policy
    - Удаление архивов старше N дней
    - _Требования: 4.4_

- [ ] 6. Реализовать flush thread
  - [ ] 6.1 Создать dedicated flush thread
    - Periodic flush (10ms) или при 80% buffer
    - Graceful shutdown
    - _Требования: 6.1, 6.2_
  - [ ] 6.2 Интегрировать formatter + hash chain + writer
    - Pipeline: pop → format → hash → write
    - _Требования: 1.1-1.4_

- [ ] 7. Реализовать экспорт (P)
  - [ ] 7.1 Реализовать syslog export
    - UDP/TCP/TLS transport
    - _Требования: 5.1_
  - [ ] 7.2 Реализовать webhook export
    - HTTP POST с retry/backoff
    - _Требования: 5.2, 5.4_

- [ ] 8. Добавить метрики и тесты
  - [ ] 8.1 Реализовать audit_get_metrics()
    - events_logged, events_dropped, avg_latency, buffer_util
    - _Требования: 6.4_
  - [ ] 8.2 Написать unit тесты
    - test_ring_buffer, test_hash_chain, test_formatters
    - _Требования: 1-6_
  - [ ]* 8.3 Написать integration тесты
    - test_full_flow, test_rotation, test_export
    - _Требования: 1-6_
  - [ ]* 8.4 Написать performance benchmarks
    - bench_emit_latency (<50μs), bench_throughput (10K/s)
    - _Требования: 6.1-6.4_

---

> **Маркеры**: `(P)` — можно выполнять параллельно после задачи 1  
> `*` — опциональные тесты, можно отложить
