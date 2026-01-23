# Memory Bridge v2.0: Technical Design

## Обзор архитектуры

Memory Bridge v2.0 расширяет существующую bi-temporal архитектуру иерархической структурой памяти и интеллектуальным routing контекста.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Interface Layer                          │
│  rlm_discover | rlm_route | rlm_extract | rlm_causal | rlm_ttl  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Memory Bridge Manager v2.0                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Hierarchical │ │   Semantic   │ │   Auto-Extraction        │ │
│  │ Memory Store │ │   Router     │ │   Engine                 │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ TTL Manager  │ │ Causal Chain │ │   Cold Start             │ │
│  │              │ │ Tracker      │ │   Optimizer              │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Persistence Layer                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ SQLite Store │ │ Embeddings   │ │  File Watcher            │ │
│  │ (Bi-temporal)│ │ Index        │ │  (TTL Refresh)           │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Компонент 1: Hierarchical Memory Store

### 1.1 Уровни иерархии

```python
class MemoryLevel(Enum):
    L0_PROJECT = 0      # Always loaded (10-20 facts)
    L1_DOMAIN = 1       # Loaded by task context (per service/domain)
    L2_MODULE = 2       # Loaded on-demand (specific modules)
    L3_CODE = 3         # C³ Crystal integration (functions/classes)

@dataclass
class HierarchicalFact:
    id: str
    content: str
    level: MemoryLevel
    domain: Optional[str]           # L1: "auth-service", "payment-service"
    module: Optional[str]           # L2: "fraud-detection", "api-contracts"
    code_ref: Optional[str]         # L3: "file:///path/to/file.py#L10-50"
    parent_id: Optional[str]        # Иерархическая связь
    children_ids: List[str]
    embedding: Optional[np.ndarray] # Для semantic search
    ttl_config: TTLConfig
    created_at: datetime            # T (system time)
    valid_from: datetime            # T' (business time)
    valid_until: Optional[datetime]
```

### 1.2 Схема БД (расширение SQLite)

```sql
-- Расширение существующей таблицы facts
ALTER TABLE facts ADD COLUMN level INTEGER DEFAULT 0;
ALTER TABLE facts ADD COLUMN domain TEXT;
ALTER TABLE facts ADD COLUMN module TEXT;
ALTER TABLE facts ADD COLUMN code_ref TEXT;
ALTER TABLE facts ADD COLUMN parent_id TEXT;
ALTER TABLE facts ADD COLUMN embedding BLOB;
ALTER TABLE facts ADD COLUMN ttl_seconds INTEGER;
ALTER TABLE facts ADD COLUMN ttl_refresh_trigger TEXT;

-- Новая таблица для иерархии
CREATE TABLE fact_hierarchy (
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relationship TEXT DEFAULT 'contains',
    PRIMARY KEY (parent_id, child_id)
);

-- Индекс для semantic search
CREATE TABLE embeddings_index (
    fact_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 1.3 API методы

```python
class HierarchicalMemoryStore:
    def add_fact(
        self, 
        content: str, 
        level: MemoryLevel,
        domain: Optional[str] = None,
        module: Optional[str] = None,
        parent_id: Optional[str] = None,
        ttl_config: Optional[TTLConfig] = None
    ) -> str:
        """Добавить факт с иерархией"""
        
    def get_facts_by_level(
        self, 
        level: MemoryLevel,
        domain: Optional[str] = None
    ) -> List[HierarchicalFact]:
        """Получить факты по уровню"""
        
    def get_subtree(self, fact_id: str) -> List[HierarchicalFact]:
        """Получить все дочерние факты"""
        
    def promote_fact(self, fact_id: str, new_level: MemoryLevel) -> None:
        """Повысить уровень факта (L2 → L1)"""
```

---

## Компонент 2: Semantic Router

### 2.1 Архитектура маршрутизации

```python
class SemanticRouter:
    def __init__(
        self, 
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.5,
        max_tokens: int = 2000
    ):
        self.model = SentenceTransformer(embedding_model)
        self.threshold = similarity_threshold
        self.max_tokens = max_tokens
    
    def route(
        self, 
        query: str, 
        store: HierarchicalMemoryStore,
        include_l0: bool = True
    ) -> RoutingResult:
        """
        Маршрутизация запроса к релевантным фактам.
        
        Returns:
            RoutingResult с отобранными фактами и confidence
        """
```

### 2.2 Алгоритм маршрутизации

```
Input: query (str), max_tokens (int)
Output: List[HierarchicalFact]

1. ALWAYS load L0 facts (project overview)
2. Compute query_embedding = embed(query)
3. For each L1 domain:
   a. Compute domain_similarity = cosine(query_embedding, domain_centroid)
   b. If domain_similarity > threshold:
      - Add domain facts to candidates
4. For candidates, rank by similarity
5. Apply token budget:
   a. Start with L0 (required)
   b. Add top-K L1 facts until budget 70%
   c. Add top-K L2 facts until budget 95%
   d. Reserve 5% for metadata
6. If total_confidence < 0.5:
   - Fallback: load broader context (more L1 domains)
7. Return selected facts with routing_explanation
```

### 2.3 Cross-Reference Resolution

```python
@dataclass
class RoutingResult:
    facts: List[HierarchicalFact]
    total_tokens: int
    routing_confidence: float
    routing_explanation: str
    cross_references: List[Tuple[str, str]]  # (fact_id, related_fact_id)
    
def resolve_cross_references(
    self, 
    primary_facts: List[HierarchicalFact],
    max_additional: int = 5
) -> List[HierarchicalFact]:
    """
    Если fact A ссылается на fact B, загрузить B тоже.
    
    Правила:
    - Decisions ссылаются на related facts
    - Module facts ссылаются на parent domain facts
    - Causal chains загружаются полностью
    """
```

---

## Компонент 3: Auto-Extraction Engine

### 3.1 Триггеры экстракции

| Trigger | Source | Fact Level |
|---------|--------|------------|
| `rlm_sync_state` | git diff | L1/L2 |
| File save | File watcher | L2/L3 |
| New file | File watcher | L1/L2 |
| README update | File watcher | L0 |
| Decision recorded | MCP tool | L0/L1 |

### 3.2 Extraction Pipeline

```python
class AutoExtractionEngine:
    def extract_from_diff(
        self, 
        diff: str, 
        context: Optional[str] = None
    ) -> List[CandidateFact]:
        """
        Извлечь факты из git diff.
        
        Heuristics:
        - New file: "Added {filename} for {purpose}"
        - Function added: "Implemented {func_name} in {module}"
        - Major refactor (>50 lines): "Refactored {module}"
        - Config change: "Updated {config} to {value}"
        """
        
    def extract_from_code(
        self, 
        file_path: str, 
        changes: List[CodeChange]
    ) -> List[CandidateFact]:
        """
        Извлечь факты из изменений кода.
        
        Uses AST analysis for:
        - New classes/functions
        - API changes (signatures)
        - Import changes (new dependencies)
        """

@dataclass
class CandidateFact:
    content: str
    confidence: float          # 0.0-1.0
    source: str                # "git_diff", "file_change", "ast_analysis"
    suggested_level: MemoryLevel
    suggested_domain: Optional[str]
    requires_approval: bool    # True if confidence < 0.8
```

### 3.3 Deduplication

```python
def deduplicate(
    self, 
    candidates: List[CandidateFact],
    existing_facts: List[HierarchicalFact],
    similarity_threshold: float = 0.85
) -> List[CandidateFact]:
    """
    Удалить дубликаты используя semantic similarity.
    
    Actions:
    - similarity > 0.95: Skip (exact duplicate)
    - similarity 0.85-0.95: Merge (update existing)
    - similarity < 0.85: Add as new
    """
```

---

## Компонент 4: TTL Manager

### 4.1 TTL Configuration

```python
@dataclass
class TTLConfig:
    ttl_seconds: int
    refresh_trigger: Optional[str]  # Glob pattern: "src/auth/**/*.py"
    on_expire: TTLAction            # MARK_STALE | ARCHIVE | DELETE
    
class TTLDefaults:
    ARCHITECTURE = TTLConfig(
        ttl_seconds=30 * 24 * 3600,  # 30 days
        refresh_trigger=None,
        on_expire=TTLAction.MARK_STALE
    )
    API_CONTRACT = TTLConfig(
        ttl_seconds=7 * 24 * 3600,   # 7 days
        refresh_trigger="**/api/**/*.py",
        on_expire=TTLAction.MARK_STALE
    )
    IMPLEMENTATION = TTLConfig(
        ttl_seconds=3 * 24 * 3600,   # 3 days
        refresh_trigger=None,
        on_expire=TTLAction.ARCHIVE
    )
    SESSION_CONTEXT = TTLConfig(
        ttl_seconds=24 * 3600,       # 24 hours
        refresh_trigger=None,
        on_expire=TTLAction.DELETE
    )
```

### 4.2 TTL Processing

```python
class TTLManager:
    def __init__(self, store: HierarchicalMemoryStore):
        self.store = store
        self.file_watcher = FileWatcher()
        
    def process_expired(self) -> TTLReport:
        """
        Обработать истёкшие факты.
        Вызывается при каждом sync_state.
        """
        
    def on_file_change(self, file_path: str) -> None:
        """
        Callback от file watcher.
        Refresh TTL для фактов с matching trigger.
        """
        
    def get_stale_facts(self) -> List[HierarchicalFact]:
        """Получить устаревшие факты для review"""
```

---

## Компонент 5: Causal Chain Tracker

### 5.1 Модель данных

```python
@dataclass
class CausalNode:
    id: str
    node_type: CausalNodeType  # DECISION | REASON | CONSEQUENCE | CONSTRAINT
    content: str
    created_at: datetime
    session_id: str
    
@dataclass
class CausalEdge:
    from_id: str
    to_id: str
    edge_type: CausalEdgeType  # CAUSES | JUSTIFIES | LEADS_TO | BLOCKS
    strength: float            # 0.0-1.0

class CausalChainTracker:
    def record_decision(
        self, 
        decision: str,
        reasons: List[str],
        consequences: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None
    ) -> str:
        """Записать decision с полным контекстом"""
        
    def query_chain(
        self, 
        query: str,  # "why did we use FastAPI?"
        max_depth: int = 5
    ) -> CausalChain:
        """Найти causal chain по запросу"""
        
    def visualize(self, chain: CausalChain) -> str:
        """Mermaid diagram для walkthrough"""
```

### 5.2 Схема БД

```sql
CREATE TABLE causal_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT NOT NULL
);

CREATE TABLE causal_edges (
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    strength REAL DEFAULT 1.0,
    PRIMARY KEY (from_id, to_id, edge_type),
    FOREIGN KEY (from_id) REFERENCES causal_nodes(id),
    FOREIGN KEY (to_id) REFERENCES causal_nodes(id)
);
```

---

## Компонент 6: Cold Start Optimizer

### 6.1 Project Type Detection

```python
class ProjectTypeDetector:
    SIGNATURES = {
        ProjectType.PYTHON: ["pyproject.toml", "setup.py", "requirements.txt"],
        ProjectType.NODEJS: ["package.json", "tsconfig.json"],
        ProjectType.RUST: ["Cargo.toml"],
        ProjectType.GO: ["go.mod"],
        ProjectType.JAVA: ["pom.xml", "build.gradle"],
        ProjectType.CSHARP: ["*.csproj", "*.sln"],
    }
    
    def detect(self, project_root: Path) -> ProjectType:
        """Определить тип проекта по сигнатурам"""
```

### 6.2 Template Seeding

```python
class TemplateSeed:
    """Стандартные факты для типа проекта"""
    
    PYTHON_TEMPLATE = [
        HierarchicalFact(
            content="Python project using {framework}",
            level=MemoryLevel.L0_PROJECT,
            ...
        ),
        # ... стандартные facts для Python
    ]
    
    def seed(
        self, 
        project_type: ProjectType,
        detected_info: Dict[str, Any]
    ) -> List[HierarchicalFact]:
        """Сгенерировать начальные факты"""
```

### 6.3 Progressive Discovery

```python
class ProgressiveDiscovery:
    def discover_for_task(
        self, 
        task_description: str,
        project_root: Path,
        existing_facts: List[HierarchicalFact]
    ) -> DiscoveryResult:
        """
        Минимальный discovery для конкретной задачи.
        
        Algorithm:
        1. Parse task_description для keywords
        2. Find relevant files (grep, fd)
        3. Extract only necessary facts
        4. Skip already known areas
        """
        
    def background_index(
        self, 
        project_root: Path,
        priority_paths: List[str]
    ) -> AsyncGenerator[HierarchicalFact, None]:
        """
        Async background indexing.
        Yields facts as they are discovered.
        """
```

---

## Компонент 7: MCP Tool Extensions

### 7.1 New Tools

```python
@server.tool()
async def rlm_discover_project(
    project_root: Optional[str] = None,
    task_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Smart cold start discovery.
    
    Args:
        project_root: Path to project (auto-detect if None)
        task_hint: Optional hint about first task
        
    Returns:
        {
            "status": "success",
            "project_type": "python",
            "facts_created": 15,
            "discovery_tokens": 5000,
            "suggested_domains": ["api", "auth", "database"]
        }
    """

@server.tool()
async def rlm_route_context(
    query: str,
    max_tokens: int = 2000,
    include_stale: bool = False
) -> Dict[str, Any]:
    """
    Semantic routing для конкретного запроса.
    
    Returns:
        {
            "status": "success",
            "facts": [...],
            "routing_confidence": 0.85,
            "routing_explanation": "Loaded auth-service and payment-service domains",
            "tokens_used": 1500
        }
    """

@server.tool()
async def rlm_extract_facts(
    source: str = "git_diff",  # git_diff | staged | file
    file_path: Optional[str] = None,
    auto_approve: bool = False
) -> Dict[str, Any]:
    """
    Auto-extract facts from changes.
    
    Returns:
        {
            "status": "success",
            "candidates": [
                {"content": "...", "confidence": 0.9, "approved": true},
                {"content": "...", "confidence": 0.6, "approved": false}
            ],
            "pending_approval": 2
        }
    """

@server.tool()
async def rlm_get_causal_chain(
    query: str,
    max_depth: int = 5
) -> Dict[str, Any]:
    """
    Query reasoning history.
    
    Returns:
        {
            "status": "success",
            "chain": {
                "root": {"type": "decision", "content": "..."},
                "reasons": [...],
                "consequences": [...]
            },
            "mermaid": "graph TD\\n..."
        }
    """

@server.tool()
async def rlm_set_ttl(
    fact_id: str,
    ttl_seconds: int,
    refresh_trigger: Optional[str] = None
) -> Dict[str, Any]:
    """Configure TTL for specific fact"""

@server.tool()
async def rlm_get_stale_facts(
    include_archived: bool = False
) -> Dict[str, Any]:
    """Get facts that need review/refresh"""
```

---

## Файловая структура

```
rlm_toolkit/memory_bridge/
├── __init__.py
├── manager.py              # MemoryBridgeManager v2.0
├── storage.py              # StateStorage (extended)
├── mcp_tools.py            # MCP tools (extended)
├── v2/
│   ├── __init__.py
│   ├── hierarchical.py     # HierarchicalMemoryStore
│   ├── router.py           # SemanticRouter
│   ├── extractor.py        # AutoExtractionEngine
│   ├── ttl.py              # TTLManager
│   ├── causal.py           # CausalChainTracker
│   ├── coldstart.py        # ColdStartOptimizer
│   └── templates/          # Project type templates
│       ├── python.yaml
│       ├── nodejs.yaml
│       ├── rust.yaml
│       └── ...
└── tests/
    ├── test_hierarchical.py
    ├── test_router.py
    ├── test_extractor.py
    ├── test_ttl.py
    ├── test_causal.py
    └── test_coldstart.py
```

---

## Migration Path

### From v1.1.0 to v2.0

1. **Database migration**: Add new columns to existing tables
2. **Fact promotion**: Existing facts → L0/L1 based on heuristics
3. **Embedding generation**: Batch compute embeddings for existing facts
4. **Backward compatibility**: v1.1.0 tools continue to work

```python
def migrate_v1_to_v2(db_path: Path) -> MigrationResult:
    """
    Non-destructive migration from v1.1.0 to v2.0.
    
    Steps:
    1. Backup existing database
    2. Add new columns (nullable)
    3. Classify existing facts by level
    4. Generate embeddings
    5. Verify integrity
    """
```

---

## Ограничения и Trade-offs

| Decision | Trade-off |
|----------|-----------|
| SQLite default | Simpler, но ограничен для >10K facts |
| Local embeddings | Работает offline, но менее точные чем API |
| Conservative TTL | Меньше потери данных, но больше stale facts |
| User approval for extraction | Качественнее, но требует attention |
