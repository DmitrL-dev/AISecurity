# Tutorial 12: Production Observability

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Monitor, trace, and control costs in production AI applications

## What You'll Learn

- Set up distributed tracing
- Track and limit LLM costs
- Integrate with Langfuse
- Build a cost dashboard

## Prerequisites

```bash
pip install rlm-toolkit[observability]
```

---

## Part 1: Basic Tracing

### 1.1 Console Tracer

```python
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, ConsoleExporter

# Create tracer with console output
tracer = Tracer(
    service_name="my-ai-app",
    exporter=ConsoleExporter(show_attributes=True)
)

# Inject into RLM
rlm = RLM.from_openai("gpt-4o", tracer=tracer)

# Run — traces appear in console
result = rlm.run("Explain quantum computing")
```

**Console output:**
```
[SPAN] rlm.run (1.24s)
  ├─ prompt_tokens: 15
  ├─ completion_tokens: 234
  └─ model: gpt-4o

[SPAN] embedding.create (0.12s)
  └─ dimensions: 1536
```

---

## Part 2: Cost Tracking

### 2.1 Set Budget

```python
from rlm_toolkit.observability import CostTracker

tracker = CostTracker(
    budget_usd=10.0,
    alert_threshold=0.8  # Alert at 80%
)

rlm = RLM.from_openai("gpt-4o", cost_tracker=tracker)

# Run queries
for i in range(100):
    if tracker.is_near_limit():
        print(f"⚠️ Budget warning at query {i}")
        break
    rlm.run(f"Question {i}")

# Final report
report = tracker.get_report()
print(f"Total spent: ${report.total_cost:.4f}")
```

### 2.2 Per-Operation Tracking

```python
# Track specific expensive operations
with tracker.track("heavy_analysis"):
    result = rlm.run(huge_document, "Detailed analysis")

print(f"Analysis cost: ${tracker.get_operation_cost('heavy_analysis'):.4f}")
```

---

## Part 3: Langfuse Integration

### 3.1 Setup

```python
from rlm_toolkit.observability import LangfuseExporter

exporter = LangfuseExporter(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com"
)

tracer = Tracer(service_name="production-api", exporter=exporter)
rlm = RLM.from_openai("gpt-4o", tracer=tracer)
```

### 3.2 View in Dashboard

1. Go to cloud.langfuse.com
2. Open your project
3. See all traces with latency, cost, tokens

---

## Part 4: Custom Spans

### 4.1 Manual Instrumentation

```python
with tracer.span("data_pipeline") as parent:
    # Step 1: Load
    with tracer.span("load_documents") as load_span:
        docs = load_all_documents()
        load_span.set_attribute("doc_count", len(docs))
    
    # Step 2: Process
    with tracer.span("process") as proc_span:
        for doc in docs:
            result = rlm.run(doc, "Summarize")
            proc_span.set_attribute("processed", True)
    
    # Step 3: Save
    with tracer.span("save_results"):
        save_to_database(results)
```

---

## Part 5: Production Dashboard

### 5.1 FastAPI Integration

```python
from fastapi import FastAPI
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, CostTracker, LangfuseExporter

app = FastAPI()

# Global observability
tracer = Tracer(service_name="api", exporter=LangfuseExporter(...))
cost_tracker = CostTracker(budget_usd=1000.0)
rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)

@app.post("/analyze")
async def analyze(text: str):
    with tracer.span("api.analyze") as span:
        span.set_attribute("input_length", len(text))
        result = rlm.run(text, "Analyze")
        return {"result": result.final_answer}

@app.get("/metrics")
async def get_metrics():
    report = cost_tracker.get_report()
    return {
        "total_cost": report.total_cost,
        "remaining": report.remaining,
        "by_model": report.by_model
    }
```

---

## Results

| Metric | Before | After |
|--------|--------|-------|
| Cost visibility | ❌ None | ✅ Real-time |
| Budget protection | ❌ No | ✅ Auto-stop |
| Debug time | 30 min | 2 min |

---

## Next Steps

- [Concept: Observability](../concepts/observability.md)
- [Tutorial: Callbacks](13-callbacks.md)
- [MCP Server](10-mcp-server.md)
