# Memory Bridge v2.1: Auto-Mode SDD

## System Design Document

**Версия:** 2.1.0  
**Дата:** 2026-01-22  
**Автор:** AI-DLC  
**Статус:** Draft

---

## 1. Проблема

Memory Bridge v2.0 предоставляет мощные enterprise-функции, но требует от LLM **явных вызовов** каждого инструмента:

```
❌ Текущий flow:
User → LLM → [вручную вызывает rlm_route_context] → [вручную вызывает rlm_record_decision] → Response
```

Это создаёт проблемы:
1. **Cognitive load на LLM** — нужно помнить вызывать tools
2. **Inconsistent usage** — иногда вызывает, иногда забывает
3. **No auto-discovery** — новые проекты требуют manual setup
4. **No git integration** — факты не извлекаются автоматически

---

## 2. Решение: Auto-Mode

### Концепция

Один MCP tool `rlm_enterprise_context()` который:
1. **Автоматически** определяет новый/существующий проект
2. **Автоматически** делает discovery или restore
3. **Автоматически** routes context под текущий запрос
4. **Возвращает** готовый контекст для injection

```
✅ Целевой flow:
User → LLM → [rlm_enterprise_context(query)] → Готовый контекст → Response
```

### Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                  rlm_enterprise_context()               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Discovery   │───▶│   Routing   │───▶│  Injection  │ │
│  │ Orchestrator│    │   Engine    │    │  Formatter  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                  │                  │        │
│         ▼                  ▼                  ▼        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ ColdStart   │    │  Semantic   │    │   Context   │ │
│  │ Optimizer   │    │   Router    │    │   Builder   │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Требования

### REQ-2.1.1: Zero-Configuration Discovery

**Описание:** При первом запуске на новом проекте автоматически:
- Определить тип проекта (Python/Node/Rust/etc)
- Seed базовые факты L0
- Discover domains
- Не требовать ручной конфигурации

**Acceptance Criteria:**
- [ ] Первый вызов на пустом проекте создаёт ≥5 L0 фактов
- [ ] Discovery занимает <3 секунд
- [ ] Не падает на edge cases (пустой проект, монорепо)

### REQ-2.1.2: Query-Aware Routing

**Описание:** Каждый запрос получает релевантный контекст:
- L0 — всегда
- L1/L2 — по semantic similarity к запросу
- Token budget — соблюдается

**Acceptance Criteria:**
- [ ] Контекст содержит ≥80% релевантных фактов
- [ ] Token budget не превышен
- [ ] Latency <500ms для 1000 фактов

### REQ-2.1.3: Causal Auto-Tracking

**Описание:** Решения автоматически записываются в causal chains:
- Detect decision patterns в ответах LLM
- Extract reasons/consequences
- Link to previous decisions

**Acceptance Criteria:**
- [ ] ≥70% решений автоматически captured
- [ ] Causal chains queryable через natural language
- [ ] Не создаёт duplicate decisions

### REQ-2.1.4: Git-Triggered Extraction

**Описание:** После git operations автоматически:
- Parse diff
- Extract significant changes
- Create fact candidates
- Auto-approve high-confidence

**Acceptance Criteria:**
- [ ] Trigger на git commit/push через hook или watcher
- [ ] ≥50% extracted фактов полезны (не noise)
- [ ] Low-confidence требует approval

### REQ-2.1.5: Single-Call Interface

**Описание:** Один MCP tool покрывает 80% use cases:

```python
result = rlm_enterprise_context(
    query="How does authentication work?",
    mode="auto",  # auto | discovery | route | extract
)
```

**Acceptance Criteria:**
- [ ] Один вызов вместо 3-5
- [ ] Backwards compatible с v2.0 tools
- [ ] Clear error messages

---

## 4. Технический дизайн

### 4.1 DiscoveryOrchestrator

```python
class DiscoveryOrchestrator:
    """Orchestrates auto-discovery decisions."""
    
    def should_discover(self) -> bool:
        """Check if project needs discovery."""
        # 1. Check if L0 facts exist
        l0_facts = store.get_facts_by_level(MemoryLevel.L0_PROJECT)
        if not l0_facts:
            return True
        
        # 2. Check if project root changed
        current_root = self._detect_project_root()
        stored_root = self._get_stored_root()
        if current_root != stored_root:
            return True
        
        # 3. Check if significant time passed (>30 days)
        last_discovery = self._get_last_discovery_time()
        if datetime.now() - last_discovery > timedelta(days=30):
            return True  # Re-discover for drift
        
        return False
    
    def discover_or_restore(self) -> ContextState:
        """Auto-decide: discover new or restore existing."""
        if self.should_discover():
            return self._run_discovery()
        else:
            return self._restore_state()
```

### 4.2 EnterpriseContextBuilder

```python
class EnterpriseContextBuilder:
    """Builds context for injection into LLM."""
    
    def build(
        self,
        query: str,
        max_tokens: int = 3000,
        include_causal: bool = True,
    ) -> EnterpriseContext:
        """Build full enterprise context."""
        
        # 1. Route facts by query
        routing_result = self.router.route(
            query=query,
            max_tokens=max_tokens - 500,  # Reserve for causal
        )
        
        # 2. Get relevant causal chains
        causal_context = ""
        if include_causal:
            chains = self.causal_tracker.query_chain(query)
            if chains:
                causal_context = self._format_causal(chains)
        
        # 3. Format for injection
        return EnterpriseContext(
            facts=routing_result.facts,
            causal_chains=causal_context,
            project_overview=self._get_project_overview(),
            total_tokens=routing_result.total_tokens + len(causal_context) // 4,
        )
```

### 4.3 MCP Tool: rlm_enterprise_context

```python
@server.tool(
    name="rlm_enterprise_context",
    description="One-call enterprise context with auto-discovery, "
    "semantic routing, and causal chains. Zero configuration required.",
)
async def rlm_enterprise_context(
    query: str,
    max_tokens: int = 3000,
    mode: str = "auto",  # auto | discovery | route | extract
    include_causal: bool = True,
    auto_extract_git: bool = False,
) -> Dict[str, Any]:
    """
    Enterprise context in one call.
    
    Modes:
    - auto: Auto-detect what's needed (recommended)
    - discovery: Force project discovery
    - route: Only route context (skip discovery check)
    - extract: Extract facts from recent git changes
    """
    try:
        # Mode handling
        if mode == "auto":
            orchestrator.discover_or_restore()
        elif mode == "discovery":
            orchestrator.force_discovery()
        
        # Build context
        context = builder.build(
            query=query,
            max_tokens=max_tokens,
            include_causal=include_causal,
        )
        
        # Optional git extraction
        if auto_extract_git:
            extractor.extract_and_store(auto_approve_threshold=0.85)
        
        return {
            "status": "success",
            "context": context.to_injection_string(),
            "facts_count": len(context.facts),
            "tokens_used": context.total_tokens,
            "causal_chains_included": bool(context.causal_chains),
            "discovery_performed": orchestrator.last_discovery_performed,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### 4.4 Git Hook Integration

```python
class GitHookManager:
    """Manages git hooks for auto-extraction."""
    
    HOOK_SCRIPT = '''#!/bin/sh
# Memory Bridge Auto-Extract Hook
python -c "from rlm_toolkit.memory_bridge.v2 import auto_extract_on_commit; auto_extract_on_commit()"
'''
    
    def install_hooks(self) -> bool:
        """Install post-commit hook."""
        hook_path = self.git_dir / "hooks" / "post-commit"
        hook_path.write_text(self.HOOK_SCRIPT)
        hook_path.chmod(0o755)
        return True
    
    def uninstall_hooks(self) -> bool:
        """Remove hooks."""
        hook_path = self.git_dir / "hooks" / "post-commit"
        if hook_path.exists():
            hook_path.unlink()
        return True
```

### 4.5 System Prompt Injection

Для LLM которые поддерживают system prompts:

```python
MEMORY_BRIDGE_SYSTEM_PROMPT = '''
You have access to Memory Bridge enterprise context.

ALWAYS call rlm_enterprise_context(query) at the START of each response
to get relevant project knowledge.

The context will include:
- Project overview and architecture (L0)
- Relevant domain/module facts (L1/L2)
- Past decisions with reasoning (causal chains)

This eliminates the need to re-discover project structure each session.
'''
```

---

## 5. Implementation Tasks

### Phase 1: Core Auto-Mode (2-3 дня)

| Task | Priority | Effort |
|------|----------|--------|
| 1.1 DiscoveryOrchestrator | Critical | 4h |
| 1.2 EnterpriseContextBuilder | Critical | 4h |
| 1.3 rlm_enterprise_context tool | Critical | 3h |
| 1.4 Tests | Critical | 4h |

### Phase 2: Git Integration (1-2 дня)

| Task | Priority | Effort |
|------|----------|--------|
| 2.1 GitHookManager | High | 3h |
| 2.2 Auto-extract on commit | High | 3h |
| 2.3 File watcher integration | Medium | 2h |

### Phase 3: Causal Auto-Tracking (2-3 дня)

| Task | Priority | Effort |
|------|----------|--------|
| 3.1 Decision pattern detector | High | 6h |
| 3.2 Auto-link to existing chains | Medium | 4h |
| 3.3 Deduplication | Medium | 2h |

### Phase 4: UX Polish (1 день)

| Task | Priority | Effort |
|------|----------|--------|
| 4.1 System prompt template | High | 2h |
| 4.2 CLI for hook installation | Medium | 2h |
| 4.3 Documentation | High | 2h |

**Total Estimate:** 6-9 дней

---

## 6. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User effort | 1 call vs 5 | Tool call count per query |
| Context relevance | ≥80% | User feedback / A/B test |
| Discovery speed | <3s | P95 latency |
| Fact extraction quality | ≥50% useful | Manual review sample |
| Causal coverage | ≥70% decisions | Comparison with manual |

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-discovery (noise facts) | Medium | Confidence thresholds, user approval for low-confidence |
| Git hook conflicts | Low | Optional installation, graceful fallback |
| Token budget exceeded | Medium | Hard limits, progressive loading |
| Causal false positives | Medium | Conservative pattern matching, review queue |

---

## 8. User Experience

### Before (v2.0)
```
User: How does auth work?
AI: [calls rlm_route_context] [calls rlm_get_causal_chain] 
    Based on context...
```

### After (v2.1 Auto-Mode)
```
User: How does auth work?
AI: [calls rlm_enterprise_context("How does auth work?")]
    Based on your project's auth module which uses JWT tokens
    (decision made 2024-12-15 because of stateless requirements)...
```

**Zero friction. Full context. Automatic.**

---

## 9. Approval

- [ ] Technical review
- [ ] User approval
- [ ] Implementation start

---

**Next Step:** Утверждение и старт Phase 1
