# RLM MCP Server v1.2 — SDD (Software Design Document)

**Версия:** 1.2  
**Дата:** 2026-01-19  
**Статус:** DRAFT — Pending Council Review  
**Цель:** 6.5/10 → 10/10

---

## 1. Критические Вопросы

### 1.1. Устаревание данных (Data Staleness)

**Проблема:**  
Crystal и память хранят snapshot проекта на момент индексации. Когда библиотека Х обновляется:
- Память содержит старую версию
- Пользователь не знает про обновление
- Принимаются решения на устаревших данных

**Примеры:**
1. `requests==2.28.0` в памяти, актуальная `2.32.0` с security fix
2. Deprecated API в памяти, новый API в docs
3. Breaking changes между версиями

### 1.2. Bootstrapping существующих проектов

**Проблема:**  
Проект SENTINEL имеет 217 engines, ~500K LOC. При каждой новой сессии:
- LLM сначала не знает о проекте
- Требуется N токенов для "обучения"
- Повторяется каждый раз

**Требуется:**
- Pre-indexed crystals для существующих проектов
- Instant load без re-parsing
- Delta updates только для изменений

---

## 2. Архитектура решения

### 2.1. Staleness Detection System

```
┌─────────────────────────────────────────────────────────────┐
│                   STALENESS DETECTOR                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ File Watcher │───▶│ Hash Compare │───▶│ Invalidator  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  PyPI Watch  │───▶│ Version Diff │───▶│ Notification │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2. Project Bootstrapping

```
┌─────────────────────────────────────────────────────────────┐
│                   PROJECT BOOTSTRAP                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Indexer    │───▶│ Crystal DB   │───▶│  Snapshot    │  │
│  │  (one-time)  │    │   (SQLite)   │    │   (.rlm/)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                             │                               │
│                             ▼                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Delta Update │◀───│  Git Diff    │───▶│ Incremental  │  │
│  │ (on change)  │    │  Detection   │    │   Index      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Staleness Detection

### 3.1. Crystal Freshness

Каждый crystal получает метаданные свежести:

```python
@dataclass
class FreshnessMetadata:
    """Track crystal freshness."""
    indexed_at: float          # Timestamp индексации
    source_mtime: float        # mtime исходного файла
    source_hash: str           # SHA-256 контента
    ttl_hours: int = 24        # Time-to-live
    
    @property
    def is_stale(self) -> bool:
        age_hours = (time.time() - self.indexed_at) / 3600
        return age_hours > self.ttl_hours
    
    @property
    def needs_revalidation(self) -> bool:
        # Check if source file changed
        current_mtime = os.path.getmtime(self.source_path)
        return current_mtime != self.source_mtime
```

### 3.2. Dependency Staleness

Автоматически проверяем обновления зависимостей:

```python
class DependencyWatcher:
    """Watch for dependency updates."""
    
    async def check_updates(self, requirements: List[str]) -> List[Update]:
        """Check PyPI for newer versions."""
        updates = []
        
        for req in requirements:
            current = self._parse_version(req)
            latest = await self._fetch_pypi_version(req.name)
            
            if latest > current:
                updates.append(Update(
                    package=req.name,
                    current=current,
                    latest=latest,
                    severity=self._classify_update(current, latest),
                    security_advisory=await self._check_advisories(req.name),
                ))
        
        return updates
    
    def _classify_update(self, current, latest) -> str:
        if latest.major > current.major:
            return "BREAKING"
        elif latest.minor > current.minor:
            return "FEATURE"
        else:
            return "PATCH"
```

### 3.3. Notification System

Уведомления пользователю о staleness:

```python
class StalenessNotifier:
    """Notify user about stale data."""
    
    def format_notification(self, stale_items: List[StaleItem]) -> str:
        lines = ["⚠️ **Обнаружены устаревшие данные:**"]
        
        for item in stale_items:
            if item.type == "crystal":
                lines.append(f"  - `{item.path}` изменён {item.age}")
            elif item.type == "dependency":
                lines.append(f"  - `{item.name}`: {item.current} → {item.latest}")
                if item.security:
                    lines.append(f"    🔴 **SECURITY:** {item.advisory}")
        
        lines.append("\nЗапустите `rlm refresh` для обновления.")
        return "\n".join(lines)
```

---

## 4. Project Bootstrapping

### 4.1. One-Time Indexing

Индексация проекта один раз, сохранение в SQLite:

```python
class ProjectIndexer:
    """Index entire project to SQLite."""
    
    def __init__(self, project_root: Path):
        self.root = project_root
        self.db_path = project_root / ".rlm" / "crystals.db"
    
    async def index_full(self) -> IndexResult:
        """Full project indexing."""
        create_db(self.db_path)
        
        files = list(self.root.glob("**/*.py"))
        extractor = HPEExtractor(use_spacy=True)
        
        for path in tqdm(files, desc="Indexing"):
            content = path.read_text()
            crystal = extractor.extract_from_file(str(path), content)
            
            self._save_to_db(crystal, FreshnessMetadata(
                indexed_at=time.time(),
                source_mtime=path.stat().st_mtime,
                source_hash=hashlib.sha256(content.encode()).hexdigest(),
            ))
        
        return IndexResult(files=len(files), crystals=len(self.db))
```

### 4.2. Delta Updates

Обновляем только изменённые файлы:

```python
class DeltaUpdater:
    """Update only changed files."""
    
    def detect_changes(self) -> List[Change]:
        """Detect changed files since last index."""
        changes = []
        
        for crystal in self.db.all_crystals():
            path = Path(crystal.path)
            
            if not path.exists():
                changes.append(Change("DELETED", path))
            elif path.stat().st_mtime != crystal.freshness.source_mtime:
                changes.append(Change("MODIFIED", path))
        
        # Check for new files
        for path in self.root.glob("**/*.py"):
            if not self.db.has_crystal(str(path)):
                changes.append(Change("ADDED", path))
        
        return changes
    
    async def apply_delta(self, changes: List[Change]) -> int:
        """Apply delta updates."""
        for change in changes:
            if change.type == "DELETED":
                self.db.delete_crystal(change.path)
            elif change.type in ("MODIFIED", "ADDED"):
                crystal = self.extractor.extract_from_file(
                    str(change.path), 
                    change.path.read_text()
                )
                self.db.upsert_crystal(crystal)
        
        return len(changes)
```

### 4.3. Git Integration

Используем git для efficient diff:

```python
class GitDeltaDetector:
    """Use git for efficient change detection."""
    
    def get_changes_since(self, commit: str) -> List[Path]:
        """Get files changed since commit."""
        result = subprocess.run(
            ["git", "diff", "--name-only", commit, "HEAD"],
            capture_output=True, text=True
        )
        return [Path(p) for p in result.stdout.strip().split("\n") if p]
    
    def get_last_indexed_commit(self) -> str:
        """Get commit when we last indexed."""
        meta_path = self.root / ".rlm" / "metadata.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())["last_commit"]
        return None
```

### 4.4. Instant Load

Загрузка pre-indexed crystals в память:

```python
class InstantLoader:
    """Load pre-indexed crystals instantly."""
    
    def load_project(self, project_root: Path) -> ProjectCrystal:
        """Load entire project from .rlm/crystals.db."""
        db_path = project_root / ".rlm" / "crystals.db"
        
        if not db_path.exists():
            raise NeedsIndexingError(f"Run: rlm index {project_root}")
        
        project = ProjectCrystal(
            path=str(project_root),
            name=project_root.name,
        )
        
        # Load all crystals from DB
        conn = sqlite3.connect(db_path)
        for row in conn.execute("SELECT * FROM crystals"):
            crystal = self._deserialize(row)
            project.add_file(crystal)
        
        # Check freshness
        stale = [c for c in project.all_crystals() if c.freshness.is_stale]
        if stale:
            logger.warning(f"{len(stale)} crystals may be stale")
        
        return project
```

---

## 5. NIOKR Tracking

### До реализации:

| Учёный | v1.1 | Gap |
|--------|------|-----|
| Dr. Crystal | 6 | No compression ratio |
| Dr. Evolve | 5 | No staleness tracking |
| Dr. Quantum | 5 | No instant load |

### После реализации:

| Учёный | Target | Что даёт |
|--------|--------|----------|
| Dr. Crystal | 8 | Freshness metadata |
| Dr. Evolve | 9 | Delta updates, git integration |
| Dr. Quantum | 9 | SQLite instant load |
| Dr. Security | 10 | Dependency advisories |

---

## 6. CLI Commands

```bash
# Полная индексация проекта
rlm index /path/to/project

# Проверка устаревания
rlm status

# Delta update
rlm refresh

# Проверка зависимостей
rlm deps check

# Загрузка в MCP server
rlm-mcp --project /path/to/project
```

---

## 7. Storage Format

### .rlm/ структура:

```
project/
├── .rlm/
│   ├── crystals.db          # SQLite с crystals
│   ├── embeddings.npy       # Cached embeddings
│   ├── metadata.json        # Last commit, timestamps
│   ├── memory.json          # H-MEM persistence
│   └── config.yaml          # Project settings
```

### SQLite Schema:

```sql
CREATE TABLE crystals (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    name TEXT,
    content BLOB,           -- Serialized crystal
    indexed_at REAL,
    source_mtime REAL,
    source_hash TEXT,
    UNIQUE(path)
);

CREATE TABLE dependencies (
    name TEXT PRIMARY KEY,
    current_version TEXT,
    latest_version TEXT,
    checked_at REAL,
    security_advisory TEXT
);

CREATE INDEX idx_path ON crystals(path);
CREATE INDEX idx_mtime ON crystals(source_mtime);
```

---

## 8. Ответы на вопросы

### Q1: Как узнать про обновление библиотеки?

**A:** DependencyWatcher периодически проверяет PyPI:
- При `rlm status` показывает outdated deps
- Security advisories помечаются 🔴
- MCP tool `rlm_deps` возвращает список обновлений

```python
# В MCP server
@server.tool("rlm_deps")
async def check_deps(context_name: str) -> Dict:
    """Check for dependency updates."""
    watcher = DependencyWatcher()
    updates = await watcher.check_updates(self.get_requirements())
    return {"updates": [u.to_dict() for u in updates]}
```

### Q2: Как загрузить SENTINEL без re-parsing?

**A:** One-time indexing + SQLite:

```bash
# Один раз:
cd /path/to/sentinel-community
rlm index .

# Теперь при каждой сессии:
rlm-mcp --project .

# MCP server загружает crystals.db мгновенно:
# - 217 engines
# - ~500K LOC
# - Загрузка: < 1 секунда
```

**Delta updates:**
```bash
# После git pull:
rlm refresh  # Обновляет только изменённые файлы
```

---

## 9. Tasks

### P0: Critical

- [ ] `rlm_toolkit/storage/sqlite.py` — SQLite persistence
- [ ] `rlm_toolkit/freshness.py` — Staleness detection
- [ ] `rlm_toolkit/cli/index.py` — CLI commands
- [ ] Integration tests

### P1: High

- [ ] `rlm_toolkit/deps/watcher.py` — Dependency watching
- [ ] Git integration for delta detection
- [ ] MCP tool `rlm_deps`

### P2: Medium

- [ ] PyPI security advisory integration
- [ ] Automatic refresh on file change
- [ ] Embeddings caching

---

## 10. Метрики успеха

| Метрика | Target |
|---------|--------|
| SENTINEL full index time | < 60 sec |
| SENTINEL load time | < 1 sec |
| Delta update 10 files | < 5 sec |
| Staleness detection | < 100ms |

---

*SDD v1.2 — Pending NIOKR Council Approval*
