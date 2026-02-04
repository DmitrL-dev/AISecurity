# OpenClaw Web Security — Tasks

## Задачи реализации

### Task 1: Shield Exec Guard
**Статус:** [x] DONE
**Файл:** `src/gateway/shield-exec-guard.ts`

- [x] Создать HTTP клиент к Shield API
- [x] Реализовать `checkExecWithShield(command)` 
- [x] Добавить graceful degradation (timeout 2s, fallback allow)
- [x] Unit тесты

### Task 2: Интеграция в Exec Approval
**Статус:** [x] DONE
**Файл:** `src/gateway/secure-exec-approval-manager.ts`

- [x] Обёртка SecureExecApprovalManager
- [x] Вызов Shield в методе `createSecure()`
- [x] Интеграция с Telegram alerts

### Task 3: RLM Audit Logger
**Статус:** [x] DONE
**Файл:** `src/gateway/rlm-audit-logger.ts`

- [x] HTTP клиент к RLM MCP server
- [x] Логировать exec events как L2 факты
- [x] Async (fire-and-forget)

### Task 4: Telegram Alerts
**Статус:** [x] DONE
**Файл:** `src/gateway/telegram-exec-alert.ts`

- [x] Интеграция с Telegram API
- [x] Алерт при risk_score > 0.7
- [x] Форматирование сообщения (HTML)
