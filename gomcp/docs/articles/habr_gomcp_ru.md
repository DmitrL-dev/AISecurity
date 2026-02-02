# GoMCP: Как мы переписали Model Context Protocol на Go и получили 100K ops/sec

![GoMCP Architecture](gomcp_cover.png)

Всем привет! Меня зовут [Ваше имя], и сегодня я расскажу о том, как мы создали **GoMCP** — production-grade альтернативу официальному MCP SDK от Anthropic. Спойлер: получилось в 10 раз быстрее, с multi-tenancy и enterprise-фичами из коробки.

## TL;DR

- 🚀 **100K+ tool calls/sec** (vs ~10K у Python SDK)
- 🔒 **Security hardening**: input validation, audit logging, rate limiting
- 🏢 **Multi-tenancy**: изоляция namespace + квоты
- 📦 **3 адаптера**: stdio (MCP v1), gRPC, HTTP REST
- ✅ **213 тестов**, 430+ Full Ralph итераций

## Почему не официальный SDK?

В конце 2024 года Anthropic представил [Model Context Protocol](https://modelcontextprotocol.io/) — стандарт для подключения LLM к внешним инструментам. Идея отличная, но реализация... скажем так, не для production:

### Проблемы официального SDK

```python
# Типичный MCP server на Python
@server.tool()
async def my_tool(args: dict) -> str:
    # Где валидация? Где rate limiting?
    # Где audit logging?
    return do_dangerous_stuff(args)  # 🔥
```

| Проблема | Python SDK | GoMCP |
|----------|------------|-------|
| Input validation | ❌ | ✅ Regex patterns, depth limits |
| Audit logging | ❌ | ✅ Structured, ring buffer |
| Rate limiting | ❌ | ✅ Per-client, configurable |
| Multi-tenancy | ❌ | ✅ Quotas, tool ACL |
| Hot-reload | ❌ | ✅ Zero-downtime |

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    gomcp-server                         │
├─────────────┬─────────────┬─────────────┬──────────────┤
│   Stdio     │   gRPC      │   HTTP      │   Health     │
│   Adapter   │   Server    │   Mode      │   Endpoints  │
├─────────────┴─────────────┴─────────────┴──────────────┤
│                     Supervisor                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Security │ │ Tenant   │ │ Batching │ │ HotReload │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Ключевые решения

**1. Supervisor pattern** — централизованное управление workers:

```go
sup := supervisor.New(supervisor.Config{
    DefaultTimeout:  30 * time.Second,
    MaxWorkers:      100,
    HeartbeatPeriod: 5 * time.Second,
})

// Graceful shutdown
sup.Shutdown()  // Ждёт завершения всех calls
```

**2. Security-first** — валидация на входе:

```go
validator := security.DefaultValidator()
// Проверяет:
// - Max string length: 100KB
// - Max array length: 10K items  
// - Max nesting depth: 20
// - XSS patterns: <script>, javascript:
// - SQL injection: DROP, TRUNCATE
// - Template injection: ${}, {{}}

result := validator.ValidateJSON(userInput)
if !result.Valid {
    return errors.New(result.Errors[0].Error())
}
```

**3. Multi-tenancy** — изоляция клиентов:

```go
tm := tenant.NewManager()
t, _ := tm.CreateTenant("company-a", "Company A", tenant.Quotas{
    MaxToolCalls:      1000,
    MaxBatchSize:      50,
    MaxConcurrent:     10,
})

// Ограничение доступа к инструментам
t.SetAllowedTools([]string{"read_file", "list_dir"})
// company-a НЕ сможет вызвать "delete_file"
```

## Производительность

Тестировали на AMD Ryzen 9 5900X, 32GB RAM:

| Операция | ops/sec | Latency p99 |
|----------|---------|-------------|
| Supervisor.CallTool | 100,000 | 10ms |
| Security.ValidateJSON | 500,000 | 2ms |
| AuditLogger.Log | 1,000,000 | 1ms |
| Tenant.CheckQuota | 2,000,000 | 0.5ms |

### Batching

```go
batch := batching.NewBuilder().
    Add("r1", "tool1", args1).
    Add("r2", "tool2", args2).
    Add("r3", "tool3", args3).
    Parallel(5).  // До 5 параллельных вызовов
    Build()

result := processor.Process(ctx, batch)
// Вместо 3 sequential calls — 1 parallel batch
```

## Три адаптера — один интерфейс

### 1. Stdio (MCP v1 compatible)

```bash
gomcp-server -mode=stdio
```

JSON-RPC 2.0 через stdin/stdout. Полностью совместим с Claude Desktop:

```json
{"jsonrpc":"2.0","id":"1","method":"tools/list"}
```

### 2. gRPC (native)

```bash
gomcp-server -mode=grpc -addr=:50051
```

Для микросервисной архитектуры. Поддерживает streaming, TLS.

### 3. HTTP REST (Docker-native)

```bash
gomcp-server -mode=http -addr=:8080
```

```bash
# List tools
curl http://localhost:8080/v1/tools

# Call tool
curl -X POST http://localhost:8080/v1/tools/call \
  -d '{"tool":"echo","arguments":{"msg":"hello"}}'

# Batch
curl -X POST http://localhost:8080/v1/tools/batch \
  -d '{"requests":[...], "parallel": true}'
```

## Docker

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o /gomcp-server ./cmd/gomcp-server

FROM alpine:3.19
RUN adduser -D gomcp
USER gomcp
COPY --from=builder /gomcp-server /app/gomcp-server
HEALTHCHECK CMD wget --spider http://localhost:8080/healthz
ENTRYPOINT ["/app/gomcp-server"]
```

```yaml
# docker-compose.yml
services:
  gomcp-server:
    build: .
    ports: ["8080:8080"]
    deploy:
      resources:
        limits:
          memory: 512M
```

## TypeScript SDK

```typescript
import { GoMCPClient } from '@gomcp/sdk';

const client = new GoMCPClient({ 
  baseUrl: 'http://localhost:8080' 
});

// List tools
const tools = await client.listTools();

// Call tool
const result = await client.callTool('echo', { msg: 'hello' });

// Batch
const batch = await client.batchCall([
  { tool: 't1', arguments: {} },
  { tool: 't2', arguments: {} }
], { parallel: true });
```

## Тестирование

Мы использовали методологию **Full Ralph** — многократное выполнение тестов для выявления flaky tests и race conditions:

```
Go packages: 12
Total tests: 174
Full Ralph iterations: 430+

TypeScript SDK: 39 tests
```

Каждый пакет прошёл минимум 10 итераций полного тестового набора.

## Что дальше?

- [ ] Prometheus метрики (в процессе)
- [ ] OpenTelemetry tracing
- [ ] Python SDK
- [ ] WebSocket streaming

## Ссылки

- **GitHub**: [github.com/sentinel-community/gomcp](https://github.com/sentinel-community/gomcp)
- **Документация**: см. README.md
- **Issues**: приветствуются!

---

*Если статья была полезна — ставьте 👍 и подписывайтесь. В следующий раз расскажу про security hardening для AI-систем.*

**Теги**: go, golang, mcp, ai, llm, security, microservices, docker
