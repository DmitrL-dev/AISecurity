# Observability

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Tracing, metrics, and cost tracking** for production AI applications

## Overview

RLM-Toolkit provides comprehensive observability through:
- **Tracer** — Distributed tracing with spans
- **CostTracker** — LLM cost monitoring with budgets
- **Exporters** — Integration with Langfuse, LangSmith, OpenTelemetry

## Quick Start

```python
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, CostTracker

# Create tracer and cost tracker
tracer = Tracer(service_name="my-app")
cost_tracker = CostTracker(budget_usd=10.0)

# Inject into RLM
rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)

# All operations are now traced
result = rlm.run("Summarize this document", context=document)

# Get cost report
report = cost_tracker.get_report()
print(f"Total cost: ${report.total_cost:.4f}")
print(f"Budget remaining: ${report.remaining:.2f}")
```

## Tracing

### Basic Tracing

```python
from rlm_toolkit.observability import Tracer, Span

tracer = Tracer(service_name="my-service")

# Manual spans
with tracer.span("process_document") as span:
    span.set_attribute("document_size", len(doc))
    result = process(doc)
    span.set_attribute("result_size", len(result))
```

### Nested Spans

```python
with tracer.span("pipeline") as parent:
    with tracer.span("extract") as child1:
        data = extract(input)
    
    with tracer.span("transform") as child2:
        transformed = transform(data)
    
    with tracer.span("load") as child3:
        load(transformed)
```

### Automatic Tracing

```python
from rlm_toolkit.observability import create_tracer

# Auto-trace all RLM operations
tracer = create_tracer(
    service_name="my-app",
    auto_instrument=True,  # Trace all LLM calls
    sample_rate=0.1        # Sample 10% in production
)
```

## Cost Tracking

### Budget Limits

```python
from rlm_toolkit.observability import CostTracker

tracker = CostTracker(
    budget_usd=50.0,
    alert_threshold=0.8,  # Alert at 80%
    on_budget_exceeded=lambda: print("Budget exceeded!")
)

# Track costs automatically
rlm = RLM.from_openai("gpt-4o", cost_tracker=tracker)

# Check status
if tracker.is_near_limit():
    print("Warning: approaching budget limit")
```

### Cost Reports

```python
report = tracker.get_report()

print(f"""
Cost Report
-----------
Total: ${report.total_cost:.4f}
By model:
  - gpt-4o: ${report.by_model['gpt-4o']:.4f}
  - gpt-3.5-turbo: ${report.by_model['gpt-3.5-turbo']:.4f}
By operation:
  - completions: ${report.by_operation['completion']:.4f}
  - embeddings: ${report.by_operation['embedding']:.4f}
Budget remaining: ${report.remaining:.2f} ({report.remaining_percent:.1f}%)
""")
```

### Per-Request Tracking

```python
# Track specific operations
with tracker.track("expensive_analysis"):
    result = rlm.run(huge_document, "Detailed analysis")

# Get operation cost
op_cost = tracker.get_operation_cost("expensive_analysis")
print(f"Analysis cost: ${op_cost:.4f}")
```

## Exporters

### Langfuse

```python
from rlm_toolkit.observability import LangfuseExporter

exporter = LangfuseExporter(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com"
)

tracer = Tracer(service_name="my-app", exporter=exporter)
```

### LangSmith

```python
from rlm_toolkit.observability import LangSmithExporter

exporter = LangSmithExporter(
    api_key="ls-...",
    project="my-project"
)

tracer = Tracer(service_name="my-app", exporter=exporter)
```

### Console (Development)

```python
from rlm_toolkit.observability import ConsoleExporter

# Pretty-print traces to console
tracer = Tracer(
    service_name="my-app",
    exporter=ConsoleExporter(show_attributes=True)
)
```

### OpenTelemetry

```python
from rlm_toolkit.observability import Tracer
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Use standard OTLP exporter
tracer = Tracer(
    service_name="my-app",
    exporter=OTLPSpanExporter(endpoint="localhost:4317")
)
```

## Production Examples

### Example 1: API Service

```python
from fastapi import FastAPI
from rlm_toolkit import RLM
from rlm_toolkit.observability import Tracer, CostTracker, LangfuseExporter

app = FastAPI()

# Global observability
tracer = Tracer(
    service_name="api",
    exporter=LangfuseExporter(...)
)
cost_tracker = CostTracker(budget_usd=1000.0)
rlm = RLM.from_openai("gpt-4o", tracer=tracer, cost_tracker=cost_tracker)

@app.post("/analyze")
async def analyze(text: str):
    with tracer.span("api.analyze") as span:
        span.set_attribute("text_length", len(text))
        result = rlm.run(text, "Analyze sentiment")
        return {"result": result.final_answer}

@app.get("/costs")
async def get_costs():
    return cost_tracker.get_report().to_dict()
```

### Example 2: Batch Processing

```python
from rlm_toolkit.observability import CostTracker

tracker = CostTracker(budget_usd=100.0)
rlm = RLM.from_openai("gpt-4o", cost_tracker=tracker)

documents = load_documents()  # 1000 docs

for i, doc in enumerate(documents):
    # Process with budget protection
    if tracker.is_near_limit():
        print(f"Stopping at doc {i}: budget limit")
        break
    
    with tracker.track(f"doc_{i}"):
        rlm.run(doc, "Summarize")

print(f"Processed {i} documents, total cost: ${tracker.get_report().total_cost:.2f}")
```

## Related

- [Providers](providers.md)
- [Tutorial: First App](../tutorials/01-first-app.md)
- [MCP Server](../mcp-server.md)
