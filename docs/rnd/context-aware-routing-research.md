# Context-Aware LLM Routing: Research & Architecture

> **Status:** Research Complete  
> **Date:** 2026-02-03  
> **Goal:** Find optimal architecture for role-based, data-aware LLM request routing

---

## Problem Statement

Enterprise LLM deployments need intelligent routing based on:

1. **WHO** — User identity, role, department
2. **WHAT** — Data classification (PII, secrets, public)
3. **WHERE** — Destination LLM (internal secure vs external)

### Example Scenarios

| # | User Role | Request | Expected Route |
|---|-----------|---------|----------------|
| 1 | HR | "данные по Иванову" (PII) | ✅ Internal LLM |
| 2 | Engineer | "данные по Иванову" (PII) | ❌ BLOCKED |
| 3 | Anyone | "бумажный самолётик" (public) | ✅ External LLM |
| 4 | Engineer | "чертежи станка" (engineering) | ✅ Internal LLM |

### Challenge

- Pattern matching doesn't scale (millions of prompt variants)
- Need semantic understanding + policy enforcement
- Low latency requirement (<100ms)

---

## Research Findings

### 1. Open Source LLM Gateways

| Solution | Routing | Data Classification | RBAC | Notes |
|----------|---------|---------------------|------|-------|
| **Portkey AI Gateway** | ✅ Advanced (conditional, geo, task-based) | ❌ External | ✅ Limited | 250+ providers, open source |
| **LiteLLM Proxy** | ✅ Load balancing, fallbacks | ❌ None | ✅ Virtual keys | 100+ LLMs, cost tracking |
| **MLflow AI Gateway** | ✅ Static/dynamic rules | ❌ None | ✅ Databricks integration | Enterprise focus |
| **Kong AI Gateway** | ✅ Standard routing | ⚠️ Via plugins | ✅ Standard | General API gateway |

**Key Insight:** None of these have built-in semantic data classification — they require external classifiers.

### 2. Semantic Routing (Critical Discovery!)

**`semantic-router` library** (Python, open source):
- Uses **embeddings** for intent classification
- **Millisecond latency** (no LLM call needed)
- Trained on example phrases, generalizes to new prompts
- Can be combined with fine-tuned BERT for uncertainty handling

```python
from semantic_router import Route, RouteLayer

pii_route = Route(
    name="pii_data",
    utterances=[
        "дай данные по Иванову",
        "покажи персональную информацию",
        "какой адрес у сотрудника",
    ]
)

engineering_route = Route(
    name="engineering",
    utterances=[
        "покажи чертежи станка",
        "схема сборки детали",
        "CAD модель",
    ]
)

public_route = Route(
    name="public",
    utterances=[
        "как сделать бумажный самолётик",
        "какая погода завтра",
        "расскажи рецепт",
    ]
)

router = RouteLayer(routes=[pii_route, engineering_route, public_route])
route = router(prompt)  # Returns route name in ~5ms
```

**This is the key to solving the "millions of patterns" problem!**

### 3. Data Classification Solutions

| Solution | Approach | Best For |
|----------|----------|----------|
| **Microsoft Presidio** | NER + regex + context | PII detection, GDPR/HIPAA |
| **GuardRails AI** | Presidio + GLiNER | LLM output validation |
| **Cloudflare AI Gateway** | DLP policies | Cloud deployments |
| **Custom BERT Classifier** | Fine-tuned model | Domain-specific |

**Microsoft Presidio** is the best open-source choice:
- 50+ PII entity types
- Customizable recognizers
- Works with any NER model
- Privacy-first design

### 4. Access Control Models

| Model | Description | Best For |
|-------|-------------|----------|
| **RBAC** | Role → Permissions matrix | Simple hierarchies |
| **ABAC** | Attributes (user, resource, context) → Decision | Dynamic policies |
| **PBAC** | Persona-based, intent-aware | LLM interactions |
| **OPA (Open Policy Agent)** | Policy-as-code (Rego) | Complex enterprise |
| **Cedar** (AWS) | RBAC+ABAC hybrid | AWS integrations |

**Key Insight:** For LLM routing, need **ABAC with semantic context** — combine user role with data classification.

### 5. Commercial Solutions Deep-Dive

#### Knostic AI (Most Relevant!)
- **Problem:** Traditional RBAC fails because LLMs can *infer* sensitive data
- **Solution:** "Knowledge Control Layer" at inference time
- **Features:**
  - Prompt simulation for access testing
  - Real-time policy enforcement
  - Persona-Based Access Control (PBAC)
  - Integration with enterprise identity

**Architecture Insight:** Knostic enforces policies at the "knowledge layer" (where AI generates answers), not at file level.

### 6. Academic Research

| Paper | Key Finding |
|-------|-------------|
| **Intent-Based LLM Routing with BERT** | Fine-tuned BERT for fast classification, LLM fallback for uncertain cases |
| **ABAC for RAG Systems** | Context-aware access using attributes at retrieval time |
| **Semantic Router for AI Agents** | Embedding similarity outperforms regex for intent detection |

---

## Recommended Architecture for SENTINEL

Based on research, here's the optimal approach:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARBITER SYSTEM                                  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        TIER 1: SHIELD (Ultra-fast)                    │  │
│  │                                                                        │  │
│  │  • Rate limiting                                                      │  │
│  │  • JWT/OIDC identity extraction → user_role, department              │  │
│  │  • Pattern-based attack blocking (injection, jailbreak)              │  │
│  │  • Latency: <5ms                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     TIER 2: SEMANTIC ROUTER (Fast)                    │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │              semantic-router (Python)                            │ │  │
│  │  │                                                                   │ │  │
│  │  │  Embedding model → Category: { pii, engineering, financial,     │ │  │
│  │  │                                 public, unknown }                │ │  │
│  │  │                                                                   │ │  │
│  │  │  Latency: ~10ms                                                  │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                    │                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │              Presidio PII Scanner                                │ │  │
│  │  │                                                                   │ │  │
│  │  │  Detects: PERSON, PHONE, EMAIL, CREDIT_CARD, SSN, LOCATION...  │ │  │
│  │  │  Latency: ~20ms                                                  │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      TIER 3: POLICY ENGINE                            │  │
│  │                                                                        │  │
│  │  Input:                                                               │  │
│  │    • user_role (from JWT)                                            │  │
│  │    • data_category (from Semantic Router)                            │  │
│  │    • pii_detected (from Presidio)                                    │  │
│  │                                                                        │  │
│  │  Policy (YAML or OPA):                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  policies:                                                       │ │  │
│  │  │    - role: hr                                                    │ │  │
│  │  │      allow: [pii, financial, public]                            │ │  │
│  │  │      route: internal_llm                                         │ │  │
│  │  │                                                                   │ │  │
│  │  │    - role: engineer                                              │ │  │
│  │  │      allow: [engineering, public]                                │ │  │
│  │  │      deny: [pii, financial]                                      │ │  │
│  │  │      route_sensitive: internal_llm                               │ │  │
│  │  │      route_public: external_llm                                  │ │  │
│  │  │                                                                   │ │  │
│  │  │    - role: guest                                                 │ │  │
│  │  │      allow: [public]                                             │ │  │
│  │  │      route: external_llm                                         │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  Output: { action: allow|block, destination: internal|external }     │  │
│  │  Latency: ~5ms                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        ROUTING DECISION                               │  │
│  │                                                                        │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │  │
│  │  │  INTERNAL   │    │  EXTERNAL   │    │   BLOCKED   │              │  │
│  │  │    LLM      │    │    LLM      │    │             │              │  │
│  │  │             │    │             │    │  403        │              │  │
│  │  │  Secure     │    │  OpenAI     │    │  Forbidden  │              │  │
│  │  │  On-prem    │    │  Claude     │    │  + Audit    │              │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

Total Latency: ~40ms (acceptable for enterprise)
```

---

## Implementation Plan for SENTINEL

### Phase 1: Semantic Router Integration (Brain)

```python
# src/brain/engines/semantic_router_engine.py
from semantic_router import Route, RouteLayer

class SemanticRouterEngine(BaseEngine):
    """Классифицирует тип данных в запросе через embeddings"""
    
    def __init__(self):
        self.routes = [
            Route(name="pii", utterances=PII_EXAMPLES),
            Route(name="engineering", utterances=ENG_EXAMPLES),
            Route(name="financial", utterances=FIN_EXAMPLES),
            Route(name="public", utterances=PUBLIC_EXAMPLES),
        ]
        self.router = RouteLayer(routes=self.routes)
    
    def analyze(self, prompt: str, context: RequestContext) -> EngineResult:
        route = self.router(prompt)
        return EngineResult(
            data_category=route.name if route else "unknown",
            confidence=route.similarity if route else 0.0
        )
```

### Phase 2: Presidio PII Scanner (Brain)

```python
# src/brain/engines/presidio_engine.py
from presidio_analyzer import AnalyzerEngine

class PresidioEngine(BaseEngine):
    """Детектирует PII через Microsoft Presidio"""
    
    def __init__(self):
        self.analyzer = AnalyzerEngine()
    
    def analyze(self, prompt: str, context: RequestContext) -> EngineResult:
        results = self.analyzer.analyze(
            text=prompt,
            language="ru",  # or "en"
            entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD"]
        )
        return EngineResult(
            pii_detected=len(results) > 0,
            pii_entities=[r.entity_type for r in results],
            pii_count=len(results)
        )
```

### Phase 3: Policy Engine (Brain)

```python
# src/brain/engines/policy_engine.py
class PolicyEngine(BaseEngine):
    """ABAC-based policy decision point"""
    
    def __init__(self, policy_file: str):
        self.policies = self.load_policies(policy_file)
    
    def evaluate(
        self, 
        user_role: str, 
        data_category: str, 
        pii_detected: bool
    ) -> PolicyDecision:
        policy = self.policies.get(user_role, self.default_policy)
        
        if data_category in policy.get("deny", []):
            return PolicyDecision(action="BLOCK", reason=f"{user_role} denied {data_category}")
        
        if data_category in policy.get("allow", []):
            route = policy.get("route_sensitive" if pii_detected else "route_public", "internal_llm")
            return PolicyDecision(action="ALLOW", destination=route)
        
        return PolicyDecision(action="BLOCK", reason="No matching policy")
```

### Phase 4: Meta-Judge Integration

```python
# Update existing Meta-Judge to include routing decision
def aggregate(self, engine_results: List[EngineResult]) -> FinalVerdict:
    # Existing threat detection...
    threat_verdict = self.aggregate_threats(engine_results)
    
    # New: Routing decision
    semantic_result = self.get_result("SemanticRouterEngine")
    presidio_result = self.get_result("PresidioEngine")
    policy_result = self.get_result("PolicyEngine")
    
    return FinalVerdict(
        threat_verdict=threat_verdict,
        routing_decision=policy_result,
        data_category=semantic_result.data_category,
        pii_detected=presidio_result.pii_detected
    )
```

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Classification Method** | Semantic Router (embeddings) | Scales to any prompt variant, no regex maintenance |
| **PII Detection** | Microsoft Presidio | Best open source, proven, customizable |
| **Policy Engine** | Custom YAML + Python | Simpler than OPA for this use case |
| **Architecture** | Brain-based (not Shield) | Requires ML, leverages existing judges |
| **Latency Target** | <50ms total | Acceptable for enterprise |

---

## Technical Inference Specification

> **Critical Question:** WHAT does this run on? Is fine-tuning required?

### Quick Answer

| Question | Answer |
|----------|--------|
| **Fine-tuning required?** | ❌ NO — uses pre-trained embedding models |
| **What is needed?** | 15-30 examples (utterances) per category |
| **Where stored?** | YAML/JSON config or vector DB (Qdrant/Pinecone) |
| **Model for Russian** | `intfloat/multilingual-e5-large` or `deepvk/USER-base` |
| **Model size** | ~1.3GB (e5-large) or ~500MB (USER-base) |
| **GPU requirements** | ❌ NOT NEEDED — runs on CPU (ONNX/FastEmbed) |

---

### 1. How Semantic Router Works (No Fine-tuning!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INFERENCE (Zero-Shot)                             │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────┐     ┌────────────────┐  │
│  │   Input          │     │   Embedding      │     │   Similarity   │  │
│  │   Prompt         │ ──▶ │   Model          │ ──▶ │   Search       │  │
│  │                  │     │   (pre-trained)  │     │   (cosine)     │  │
│  │ "данные по       │     │                  │     │                │  │
│  │  Иванову"        │     │  768-dim vector  │     │  top-1 match   │  │
│  └──────────────────┘     └──────────────────┘     └────────────────┘  │
│                                                              │          │
│                                                              ▼          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    PRE-COMPUTED ROUTE EMBEDDINGS                 │  │
│  │                                                                    │  │
│  │  Route: "pii"          [0.23, -0.45, 0.12, ...]  ← avg of 20     │  │
│  │  Route: "engineering"  [0.67, 0.11, -0.33, ...]    examples      │  │
│  │  Route: "financial"    [-0.12, 0.89, 0.05, ...]                  │  │
│  │  Route: "public"       [0.01, 0.02, 0.78, ...]                   │  │
│  │                                                                    │  │
│  │  These embeddings are computed ONCE at startup!                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  Result: Route="pii", similarity=0.89, latency=~10ms                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Principle:**
- Embedding model is ALREADY trained to understand semantics (on billions of texts)
- We only provide EXAMPLES for each category
- Cosine similarity finds the closest category

---

### 2. Embedding Model Selection for Russian

| Model | Size | GPU | RU Quality | Latency | Recommendation |
|-------|------|-----|------------|---------|----------------|
| `intfloat/multilingual-e5-large` | 1.3GB | ❌ | ⭐⭐⭐⭐⭐ | ~50ms | **Production** |
| `deepvk/USER-base` | 500MB | ❌ | ⭐⭐⭐⭐ | ~30ms | **RU-only** |
| `paraphrase-multilingual-MiniLM-L12-v2` | 470MB | ❌ | ⭐⭐⭐ | ~15ms | Fast |
| `BAAI/bge-m3` | 2.2GB | ⚠️ | ⭐⭐⭐⭐⭐ | ~80ms | Maximum quality |

**For SENTINEL recommended:** `intfloat/multilingual-e5-large`
- Best on ruMTEB benchmark
- Works on CPU via ONNX
- Supports 50+ languages (RU/EN/...)

---

### 3. Examples (Utterances) — How Many Needed?

| Category | Minimum | Recommended | For 95%+ accuracy |
|----------|---------|-------------|-------------------|
| pii | 10 | **20-30** | 45+ |
| engineering | 10 | **20-30** | 45+ |
| financial | 10 | **20-30** | 45+ |
| public | 15 | **30-50** | 60+ |

**Quality Formula:**
```
Accuracy ≈ 85% + (log2(examples) × 5%)
- 10 examples → ~85%
- 20 examples → ~90%
- 40 examples → ~92-96%
```

---

### 4. Route Configuration (routes.yaml)

```yaml
# config/routes.yaml — NOT CODE, just data!

routes:
  - name: pii
    description: "Requests with personal data"
    utterances:
      # Names
      - "дай данные по Иванову"
      - "покажи информацию о сотруднике Петрове"
      - "какой адрес у Сидоровой"
      - "найди контакты менеджера Козлова"
      - "ФИО директора"
      
      # Contact info
      - "какой телефон у клиента"
      - "покажи email Анны"
      - "домашний адрес сотрудника"
      
      # Passport data
      - "серия и номер паспорта"
      - "данные паспорта Иванова"
      - "СНИЛС сотрудника"
      - "ИНН физлица"
      
      # Salaries
      - "какая зарплата у Петрова"
      - "покажи доход менеджера"
      # # Add 10-15 more examples...
    
  - name: engineering
    description: "Engineering/technical information"
    utterances:
      - "покажи чертежи станка"
      - "схема сборки детали"
      - "CAD модель корпуса"
      - "спецификация материалов"
      - "технологическая карта"
      - "допуски и посадки"
      - "3D модель редуктора"
      # # Add 10-20 more examples...

  - name: public
    description: "Public information"
    utterances:
      - "как сделать бумажный самолётик"
      - "какая погода завтра"
      - "расскажи рецепт борща"
      - "что такое машинное обучение"
      # # Add 20-40 more examples...

settings:
  embedding_model: "intfloat/multilingual-e5-large"
  similarity_threshold: 0.7  # Minimum match threshold
  fallback_route: null       # null = BLOCK on unknown category
```

---

### 5. Loading and Inference Code

```python
# src/brain/engines/semantic_router_engine.py

from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder
import yaml

class SemanticRouterEngine(BaseEngine):
    """
    Classifies data type in request via embeddings.
    
    DOES NOT REQUIRE fine-tuning — uses pre-trained models.
    Examples loaded from YAML config.
    """
    
    def __init__(self, config_path: str = "config/routes.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Initialize embedding model (pre-trained, NO fine-tuning)
        self.encoder = HuggingFaceEncoder(
            model_name=config['settings']['embedding_model']
        )
        
        # Create routes from config
        routes = []
        for route_config in config['routes']:
            routes.append(Route(
                name=route_config['name'],
                utterances=route_config['utterances']  # Examples!
            ))
        
        # RouteLayer computes example embeddings ONCE
        self.router = RouteLayer(encoder=self.encoder, routes=routes)
        self.threshold = config['settings']['similarity_threshold']
    
    def analyze(self, prompt: str, context: RequestContext) -> EngineResult:
        """Classification in ~10ms on CPU."""
        result = self.router(prompt)
        
        if result is None or result.similarity < self.threshold:
            return EngineResult(
                data_category="unknown",
                confidence=0.0,
                matched_route=None
            )
        
        return EngineResult(
            data_category=result.name,
            confidence=result.similarity,
            matched_route=result.name
        )
```

---

### 6. Alternative: FastEmbed (Even Faster, No PyTorch)

```python
# For production with minimal dependencies
from semantic_router.encoders import FastEmbedEncoder

encoder = FastEmbedEncoder(
    model_name="intfloat/multilingual-e5-large"
)
# Uses ONNX runtime — works on CPU without PyTorch
# Latency: ~5-10ms vs ~50ms with PyTorch
```

---

### 7. When IS Fine-tuning Needed?

| Scenario | Fine-tuning needed? | What to do |
|----------|---------------------|------------|
| Standard categories (PII, engineering, public) | ❌ NO | Use pre-trained + examples |
| Specific domain (medical, legal) | ⚠️ MAYBE | Try with examples first |
| Low quality (<85% accuracy) | ⚠️ MAYBE | 1) Add more examples 2) Fine-tune if that doesn't help |
| Highly specialized jargon | ✅ YES | Fine-tune on corporate data |

**When fine-tuning is definitely needed:**
- Accuracy < 80% even with 50+ examples per category
- Company-specific jargon
- Very semantically similar categories (require finer distinction)

---

### 8. Infrastructure Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4GB | 8GB |
| **GPU** | ❌ Not needed | ❌ Not needed |
| **Disk** | 2GB (model) | 5GB |
| **Python** | 3.9+ | 3.11+ |

**Dependencies:**
```
semantic-router>=0.1.0
sentence-transformers>=2.2.0  # or fastembed
pyyaml>=6.0
```

---

### 9. Process for Adding New Categories

```
1. Add to routes.yaml:
   - name: "legal"
     utterances:
       - "договор аренды"
       - "юридическое заключение"
       - ... (15-30 examples)

2. Restart service (embeddings recalculated)

3. Test:
   curl -X POST /api/classify -d '{"prompt": "составь договор"}'
   # → {"category": "legal", "confidence": 0.91}

4. Iterate: if accuracy < 90%, add more examples
```

**Time to add new category: ~30 minutes (writing examples + testing)**

---

## Enterprise Security R&D (2025-2026)

> **Expanded Research:** High-security enterprise requirements for government, military, banking, and compliance sectors.

### 1. Regulatory Frameworks Update (2025-2026)

#### OWASP Top 10 for LLM Applications 2025
Foundational standard for LLM security risks:
1. **Prompt Injection** — #1 risk, direct/indirect attack vectors
2. **Sensitive Information Disclosure** — PII/IP leakage through prompts or training data
3. **Supply Chain Vulnerabilities** — Pre-trained models, datasets, third-party tools
4. **Data and Model Poisoning** — Corrupted training data affecting behavior
5. **System Prompt Leakage** — Extraction of system instructions
6. **Vector and Embedding Weaknesses** — RAG pipeline vulnerabilities
7. **Excessive Agency** — Unauthorized autonomous actions
8. **Unbounded Consumption** — Resource exhaustion attacks

#### NIST AI RMF Updates (2025-2026)
- **Generative AI Profile (July 2024+):** Specific guidance for LLM risks
- **2025 Updates:** System Cards, Model Cards, Use-Case Inventories
- **Emergent Risks:** Over-reliance, cascading systemic failures
- **Measurement Guidance:** Fairness indicators, robustness measures, privacy leakage testing
- **2026 Focus:** AI agents, autonomous systems, ecosystem-level risks

#### EU AI Act Timeline (Critical for European Operations)
| Date | Milestone |
|------|-----------|
| Feb 2, 2025 | Prohibited practices + AI literacy training (in force) |
| Aug 2, 2025 | GPAI model obligations (transparency, documentation) |
| **Aug 2, 2026** | **Full high-risk AI requirements (Annex III)** |

**High-Risk Categories:** Biometrics, critical infrastructure, employment, education, law enforcement, border control.

**Penalties:** Up to €35M or 7% global turnover for prohibited practices; €15M or 3% for high-risk violations.

#### ФСТЭК Приказ № 117 (Russian Federation — Critical!)
> **First Russian regulatory act for AI in government systems.** Effective March 1, 2026.

**Key Requirements:**
- **Scope:** ALL government information systems (ГИС), state enterprises, municipal systems
- **AI Interaction Control:** Mandatory filtering for user-AI communication (fixed scenarios + free-form input)
- **Response Verification:** Built-in quality/correctness checking, error logging and analysis
- **Prohibition of Autonomous Changes:** AI cannot modify system parameters/architecture without confirmation
- **Cloud AI Restrictions:** Critical data processing prohibited in public clouds (only ГЕОП/ГосТех)
- **Personnel:** ≥30% of security staff must have specialized education

**Implications for SENTINEL:**
- Must support on-premise/air-gapped deployments for Russian government clients
- Response validation layer required (Brain already has this via Meta-Judge)
- Comprehensive audit logging mandatory

---

### 2. Advanced Authorization Models (2025-2026)

| Model | Description | LLM Use Case |
|-------|-------------|--------------|
| **RBAC** | Role → Permissions | Baseline model access (who can use which LLMs) |
| **ABAC** | User + Resource + Context → Decision | Dynamic, context-aware routing (department + sensitivity + time) |
| **ReBAC** | Relationship-based (graph model) | RAG document filtering, organizational hierarchies |
| **PBAC** | Persona-based (Knostic approach) | "Need-to-know" knowledge layer for LLM inference |

#### Key Architectural Pattern: Fine-Grained Authorization (FGA)
- **Zanzibar-style** permission graphs (Google's internal system, now open-source)
- **Tools:** Permit.io, SpiceDB, WorkOS FGA (GA November 2025)
- **RAG Security:** Check permissions BEFORE vector retrieval AND BEFORE context injection

```python
# Example: ReBAC check before RAG retrieval
def secure_rag_query(user, query, vector_db):
    # 1. Get user's accessible document set
    accessible_docs = permission_engine.get_accessible_resources(user, "document:read")
    
    # 2. Filter vector search to only accessible docs
    results = vector_db.search(query, filter={"doc_id": {"$in": accessible_docs}})
    
    # 3. Inject filtered context to LLM
    return llm.generate(query, context=results)
```

---

### 3. Agentic AI Security (2025-2026 Emerging!)

> **By 2026, multi-agent systems will be the default design pattern for enterprise AI.**

#### Key Security Challenges
- **Agent IDs as First-Class Actors** — Agents need distinct identities in auth systems
- **Dynamic Permission Delegation** — OAuth2 evolution for agent-to-agent authorization
- **Behavioral Monitoring** — Cost anomalies, spawning patterns, tool usage deviations
- **Memory Poisoning** — Attacks on agent memory/context stores
- **Coordination Attacks** — Compromised agents amplifying impact

#### OWASP Top 10 for Agentic Applications 2026 (Draft)
- Focuses on autonomous decision-making risks
- Tool abuse and excessive agency
- Multi-agent coordination vulnerabilities

#### Protocols and Standards
- **Agent2Agent (A2A):** Secure multi-agent communication (Google-led)
- **Agent Payments Protocol (AP2):** Financial transaction authorization for agents
- **Non-Human Identity (NHI):** CSA framework for machine/agent identity management

---

### 4. Confidential Computing for AI (2025-2026)

> **Gartner:** By 2029, 75%+ of workloads on untrusted infrastructure will use confidential computing.

| Technology | Vendor | Maturity | AI Focus |
|------------|--------|----------|----------|
| **Intel SGX** | Intel | Production | Enclave-level isolation, attestation |
| **AMD SEV-SNP** | AMD | Production | VM-level encryption, used by WhatsApp AI (2025) |
| **NVIDIA GPU CC** | NVIDIA | Production | GPU memory encryption, BlueField Astra (2026) |
| **Intel Crescent Island** | Intel | H2 2026 | Inference-focused datacenter GPUs |

**Market Growth:** $24.24B (2025) → $350B (2032), CAGR 46.4%

**Key Use Cases:**
- Encrypted inference with proprietary models
- Confidential RAG (feed sensitive docs without exposure)
- Confidential fine-tuning (proprietary training data)
- Air-gapped but verifiable cloud deployments

---

### 5. Russian Language NLP Stack (2025-2026)

| Component | Recommendation | Notes |
|-----------|----------------|-------|
| **NER Model** | DeepPavlov (`ner_collection3_bert`) | F1=0.78+ for PERSON, 18 entity types |
| **Lightweight NER** | Natasha (SlovNet) | 30MB, CPU-fast, 1-2% below SOTA |
| **spaCy Integration** | `ru_spacy_ru_updated` | F1=0.83 for PERSON |
| **Embedding Model** | `intfloat/multilingual-e5-large` | Best on ruMTEB benchmark |
| **PII Framework** | Presidio + Custom Recognizers | Russian patterns: ИНН, СНИЛС, passport |

**Benchmarks for Russian:**
- **ruMTEB:** 23 datasets, 7 task groups (retrieval, classification, clustering)
- **RusBEIR:** Zero-shot IR evaluation
- **RUSSE:** Semantic classification (Russian SuperGLUE)

**Custom Presidio Recognizers (Required):**
```python
# Russian passport pattern
class RussianPassportRecognizer(EntityRecognizer):
    PATTERNS = [
        Pattern("ru_passport", r"\b\d{2}\s?\d{2}\s?\d{6}\b", 0.7),
    ]
    SUPPORTED_ENTITY = "RU_PASSPORT"

# Russian tax ID (ИНН)
class INNRecognizer(EntityRecognizer):
    PATTERNS = [
        Pattern("inn_12", r"\b\d{12}\b", 0.6),  # Individual
        Pattern("inn_10", r"\b\d{10}\b", 0.5),  # Legal entity
    ]
    SUPPORTED_ENTITY = "RU_INN"
```

---

### 6. Enterprise LLM Gateway Architecture (2025-2026)

#### vLLM Semantic Router (v0.1 — Early 2026)
- Open-source semantic caching
- Multi-factor routing logic
- Modularity for custom policies

#### Key Gateway Features (Required for Enterprise)
| Feature | Purpose |
|---------|---------|
| **Unified API** | Single interface to 250+ LLM providers |
| **Semantic Caching** | Reduce redundant calls, cost savings |
| **Token-Aware Rate Limits** | Budget enforcement per user/department |
| **PII Redaction** | Auto-mask before external LLM calls |
| **Audit Logging** | Prompts, responses, timestamps, user context |
| **Model Failover** | Automatic retry with fallback models |
| **Geo-Routing** | Data residency compliance (EU, RU, US) |

---

### 7. ISO/IEC Compliance Stack

| Standard | Focus | SENTINEL Relevance |
|----------|-------|-------------------|
| **ISO 27001** | Information Security Management | Foundation for all security controls |
| **ISO 27701** | Privacy Information Management | PII handling, GDPR/152-FZ alignment |
| **ISO 42001** | AI Management System | AI-specific governance (first ever, Dec 2023) |

**Integration:** These three form the "ISO Trust Triad" — single unified management system approach.

---

### 8. Implementation Roadmap for SENTINEL Arbiter

#### Phase 1: Foundation (Current Sprint)
- [ ] Semantic Router engine integration
- [ ] Presidio engine with Russian recognizers
- [ ] Basic YAML policy engine

#### Phase 2: Enterprise Authorization (Q1 2026)
- [ ] ABAC policy engine (OPA/Rego evaluation)
- [ ] ReBAC integration for RAG filtering
- [ ] LDAP/AD/OIDC identity sync

#### Phase 3: High-Security Compliance (Q2 2026)
- [ ] ФСТЭК 117 compliance mode
- [ ] Air-gapped deployment profile
- [ ] Response validation layer (per Russian requirements)
- [ ] Comprehensive audit log export (SIEM-ready)

#### Phase 4: Agentic AI Support (H2 2026)
- [ ] Agent identity framework
- [ ] Multi-agent authorization
- [ ] Behavioral monitoring dashboard

---

## References

### Open Source Projects
- [semantic-router](https://github.com/aurelio-labs/semantic-router) — Embedding-based routing
- [Microsoft Presidio](https://microsoft.github.io/presidio/) — PII detection
- [Portkey AI Gateway](https://github.com/Portkey-AI/gateway) — Multi-LLM routing
- [LiteLLM](https://github.com/BerriAI/litellm) — LLM proxy
- [GuardRails AI](https://github.com/guardrails-ai/guardrails) — LLM output validation

### Commercial Solutions
- [Knostic AI](https://knostic.ai) — Knowledge access control for LLMs
- [Cloudflare AI Gateway](https://developers.cloudflare.com/ai-gateway/) — Edge AI security
- [TrueFoundry](https://truefoundry.com) — Enterprise LLM platform

### Policy Languages
- [OPA (Open Policy Agent)](https://www.openpolicyagent.org/) — Policy-as-code
- [Cedar](https://www.cedarpolicy.com/) — AWS authorization language

### Academic Papers
- "Intent-Based LLM Routing with Uncertainty-Driven Fallback" (arXiv)
- "ABAC for RAG: Attribute-Based Access Control in Retrieval-Augmented Generation"
- "Semantic Routing: Superfast Decision Layer for LLMs"

### Regulatory and Standards (2025-2026)
- [OWASP Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [OWASP Top 10 for Agentic Applications 2026](https://owasp.org/projects/)
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
- [EU AI Act](https://artificialintelligenceact.eu/)
- [ФСТЭК БДУ (Банк данных угроз)](https://bdu.fstec.ru/)
- [ФСТЭК Приказ № 117](https://fstec.ru/)
- [ISO/IEC 42001:2023 — AI Management System](https://www.iso.org/standard/81230.html)

### Confidential Computing
- [Confidential Computing Consortium](https://confidentialcomputing.io/)
- [Intel SGX](https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions/overview.html)
- [AMD SEV](https://www.amd.com/en/developer/sev.html)
- [NVIDIA Confidential Computing](https://developer.nvidia.com/confidential-computing)

### Russian NLP Resources
- [DeepPavlov](https://deeppavlov.ai/)
- [Natasha NER](https://github.com/natasha/natasha)
- [ruMTEB Benchmark](https://github.com/ai-forever/ruMTEB)
- [RusBEIR](https://github.com/ai-forever/RusBEIR)
