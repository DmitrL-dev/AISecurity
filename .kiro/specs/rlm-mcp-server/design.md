# RLM-Toolkit MCP Server: Design

## Финальная архитектура (утверждено 2026-01-19)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Antigravity / Cursor / Claude                 │
│                         (MCP Client)                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │ stdio transport
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RLM MCP Server                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                     Tool Registry                        │    │
│  │  rlm_load  │  rlm_query  │  rlm_analyze  │  rlm_memory  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    Core Engines                          │    │
│  │                                                          │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │    │
│  │  │     C³      │  │   H-MEM     │  │  InfiniRetri    │  │    │
│  │  │ (Crystals)  │  │  (Memory)   │  │  (Retrieval)    │  │    │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │    │
│  │         │                │                  │           │    │
│  │  ┌──────┴──────────────────────────────────┴────────┐  │    │
│  │  │              Storage Layer (.rlm/)                │  │    │
│  │  │  contexts/ │ crystals/ │ memory/ │ cache/         │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Provider Router                         │    │
│  │    Ollama (local)  │  OpenAI  │  Anthropic  │  Google   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Иерархия Crystals (Вариант C)

```
ProjectCrystal (проект целиком)
├── metadata:
│   ├── name: "sentinel-community"
│   ├── root_path: "/path/to/project"
│   ├── last_updated: "2026-01-19T10:00:00"
│   └── file_count: 217
│
├── global_entities:
│   ├── User, Database, API, Engine...
│   └── cross-file relations
│
├── ModuleCrystal: "brain/"
│   ├── entities: [Brain, Engine, ...]
│   ├── dependencies: [torch, numpy]
│   └── FileCrystal[]: 
│       ├── "brain/__init__.py"
│       └── "brain/engine.py"
│
└── ModuleCrystal: "rlm-research/"
    └── ...
```

---

## Hybrid Retrieval Strategy

```
Query: "Найди использование User"

Step 1: Local Model (Llama 3B) via Ollama
        → Attention-based retrieval
        → Returns: [chunk_1, chunk_5, chunk_12]

Step 2: Cloud Model (GPT-4o) via API
        → Processes only relevant chunks
        → Returns: Final answer

Benefit: InfiniRetri quality + Cloud generation quality
```

---

## Storage Structure

```
project_root/
└── .rlm/                       # RLM data directory
    ├── config.json             # Project config
    ├── crystals/
    │   ├── project.crystal     # ProjectCrystal (SQLite)
    │   └── modules/            # ModuleCrystals
    │       ├── brain.crystal
    │       └── engines.crystal
    ├── memory/
    │   ├── episodes.db         # Episode memory (SQLite)
    │   └── traces.db           # Consolidated traces
    ├── cache/
    │   └── embeddings/         # Cached embeddings
    └── .key                    # Encryption key (gitignored)
```

---

## MCP Tools Specification

### rlm_load_context
```json
{
  "name": "rlm_load_context",
  "description": "Загрузить файл или директорию в контекст",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Путь к файлу или директории"},
      "name": {"type": "string", "description": "Имя контекста (опционально)"}
    },
    "required": ["path"]
  }
}
```

### rlm_query
```json
{
  "name": "rlm_query",
  "description": "Поиск в загруженном контексте",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {"type": "string"},
      "context_name": {"type": "string"}
    },
    "required": ["question"]
  }
}
```

### rlm_analyze
```json
{
  "name": "rlm_analyze",
  "description": "Глубокий анализ через C³",
  "inputSchema": {
    "type": "object",
    "properties": {
      "context_name": {"type": "string"},
      "goal": {"type": "string", "enum": ["summarize", "find_bugs", "security_audit", "explain"]}
    },
    "required": ["goal"]
  }
}
```

### rlm_memory
```json
{
  "name": "rlm_memory",
  "description": "Управление памятью (H-MEM)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": {"type": "string", "enum": ["recall", "forget", "consolidate", "list"]},
      "topic": {"type": "string"}
    },
    "required": ["action"]
  }
}
```

---

## Конфигурация

```json
// .rlm/config.json
{
  "version": "1.0",
  "project_name": "sentinel-community",
  "providers": {
    "retrieval": "ollama:llama3:3b",
    "generation": "auto"
  },
  "storage": {
    "encryption": true,
    "max_memory_mb": 500
  },
  "crystal": {
    "update_strategy": "incremental",
    "include": ["**/*.py", "**/*.md"],
    "exclude": ["node_modules", ".git", "__pycache__"]
  }
}
```

---

## Фазовая реализация

| Фаза | Компоненты | Статус |
|------|------------|--------|
| MVP | MCP Server, rlm_load, rlm_query | ⬜ Planned |
| v0.2 | C³, rlm_analyze, Hierarchy | ⬜ Planned |
| v0.3 | H-MEM, rlm_memory | ⬜ Planned |
| v1.0 | Polish, Encryption, Installer | ⬜ Planned |

---

*Статус: ГОТОВО К РЕВЬЮ*
