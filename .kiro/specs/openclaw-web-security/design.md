# OpenClaw Web Security — Design

## Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                          │
│                                                              │
│  ┌─────────────┐    ┌────────────────┐    ┌──────────────┐  │
│  │ Control UI  │───▶│ Exec Approval  │───▶│   Shield     │  │
│  │   :18789    │    │   Manager      │    │  Middleware  │  │
│  └─────────────┘    └───────┬────────┘    └──────┬───────┘  │
│                             │                     │          │
│                             ▼                     ▼          │
│                    ┌────────────────┐    ┌──────────────┐   │
│                    │  RLM Logger    │    │ SENTINEL     │   │
│                    │  (audit)       │    │ Shield :8081 │   │
│                    └────────────────┘    └──────────────┘   │
│                             │                     │          │
│                             ▼                     ▼          │
│                    ┌────────────────┐    ┌──────────────┐   │
│                    │ Telegram Alert │    │ Block/Allow  │   │
│                    └────────────────┘    └──────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Shield Middleware
**Файл:** `src/gateway/shield-exec-guard.ts`

```typescript
interface ShieldExecResult {
  allowed: boolean;
  threats: string[];
  risk_score: number;
}

async function checkExecWithShield(command: string): Promise<ShieldExecResult>
```

### 2. RLM Audit Logger
**Файл:** `src/gateway/rlm-audit-logger.ts`

- Вызывает `rlm_add_hierarchical_fact` через HTTP
- Domain: `openclaw`, Level: L2

### 3. Telegram Alerter
**Интеграция:** Использует существующий `TelegramNotifier` из SAA

## Изменения

### [MODIFY] exec-approval-manager.ts
- Добавить вызов Shield middleware перед созданием approval record

### [NEW] shield-exec-guard.ts
- HTTP клиент к SENTINEL Shield
- Graceful degradation при недоступности

### [NEW] rlm-audit-logger.ts
- Логирование exec событий в RLM

## API контракт

Shield вызов:
```
POST http://localhost:8081/api/analyze
Content-Type: application/json

{"text": "rm -rf /", "context": "exec_approval"}
```

RLM вызов:
```
POST http://localhost:3847/rlm/add_fact
Content-Type: application/json

{"content": "[openclaw:exec] command=..., result=...", "domain": "openclaw", "level": 2}
```
