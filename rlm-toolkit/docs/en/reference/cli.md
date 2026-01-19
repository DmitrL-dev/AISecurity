# CLI Reference

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Command Line Interface** for RLM-Toolkit

## Installation

CLI is included with RLM-Toolkit:

```bash
pip install rlm-toolkit
rlm --help
```

## Commands

### rlm run

Execute RLM query from command line:

```bash
# Basic query
rlm run --model ollama:llama3 --query "Explain AI"

# With context file
rlm run --model openai:gpt-4o --context report.pdf --query "Summarize key findings"

# With options
rlm run \
  --model anthropic:claude-3 \
  --context large_document.txt \
  --query "Extract all dates" \
  --max-iterations 20 \
  --max-cost 5.0 \
  --output results.json
```

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | LLM provider:model | Required |
| `--context` | Input file/directory | - |
| `--query` | Question to ask | Required |
| `--max-iterations` | Max RLM iterations | 50 |
| `--max-cost` | Budget in USD | 10.0 |
| `--output` | Output file (json/txt) | stdout |

### rlm eval

Run benchmarks:

```bash
# OOLONG benchmark
rlm eval oolong --model ollama:llama3 --dataset ./oolong_pairs.json

# Custom benchmark
rlm eval custom --model openai:gpt-4o --test-file ./my_tests.yaml

# With detailed output
rlm eval oolong --model ollama:llama3 --verbose --report eval_report.html
```

**Options:**

| Option | Description |
|--------|-------------|
| `--dataset` | Path to test dataset |
| `--verbose` | Show per-example results |
| `--report` | Generate HTML report |
| `--parallel` | Run tests in parallel |

### rlm trace

Analyze session traces:

```bash
# Show latest session
rlm trace --session latest

# Show specific session
rlm trace --session abc123

# Export traces
rlm trace --session latest --export traces.json

# Cost analysis
rlm trace --session latest --costs
```

**Output example:**
```
Session: abc123
Started: 2026-01-19 10:30:00
Duration: 45.2s
-----------------------
Traces: 12
  - rlm.run: 8
  - embedding: 3
  - completion: 1

Cost breakdown:
  - gpt-4o: $0.0342
  - ada-002: $0.0001
  Total: $0.0343
```

### rlm index

Index a project:

```bash
# Full index
rlm index /path/to/project

# Delta update
rlm index /path/to/project --delta

# Force reindex
rlm index /path/to/project --force

# Show stats
rlm index /path/to/project --stats
```

### rlm repl

Interactive REPL:

```bash
# Start REPL
rlm repl --model ollama:llama3

# With memory
rlm repl --model openai:gpt-4o --memory

# With loaded context
rlm repl --model ollama:llama3 --context ./src
```

**REPL commands:**
```
>>> /help              # Show help
>>> /load file.txt     # Load context
>>> /memory            # Show memory stats
>>> /cost              # Show cost so far
>>> /export chat.json  # Export conversation
>>> /quit              # Exit
```

## Examples

### Example 1: Code Analysis Pipeline

```bash
#!/bin/bash
# analyze_codebase.sh

# Index the project
rlm index ./my_project --force

# Run security audit
rlm run \
  --model openai:gpt-4o \
  --context ./my_project \
  --query "Find security vulnerabilities" \
  --output security_report.json

# Generate summary
rlm run \
  --model ollama:llama3 \
  --context security_report.json \
  --query "Summarize findings in markdown" \
  --output SECURITY_AUDIT.md
```

### Example 2: Document Processing

```bash
# Process multiple documents
for doc in ./documents/*.pdf; do
  rlm run \
    --model ollama:llama3 \
    --context "$doc" \
    --query "Extract key points as JSON" \
    --output "$(basename "$doc" .pdf).json"
done

# Merge results
rlm run \
  --model openai:gpt-4o \
  --context ./documents/*.json \
  --query "Create unified summary" \
  --output combined_summary.md
```

### Example 3: Interactive Research

```bash
# Start research session with memory
rlm repl --model openai:gpt-4o --memory

>>> /load research_papers/
Loaded 45 files (12.3 MB)

>>> What are the main themes across these papers?
Analyzing... Found 5 main themes: ...

>>> /memory
Episodes: 2
Traces: 1

>>> Dive deeper into theme #3
Theme 3 analysis: ...

>>> /export research_session.json
Exported to research_session.json

>>> /quit
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `RLM_DEFAULT_MODEL` | Default model |
| `RLM_MAX_COST` | Default budget |

### Config File

Create `~/.rlm/config.yaml`:

```yaml
default_model: ollama:llama3
max_cost: 10.0
max_iterations: 50
observability:
  enabled: true
  exporter: console
```

## Related

- [Quickstart](../quickstart.md)
- [MCP Server](../mcp-server.md)
- [Observability](observability.md)
