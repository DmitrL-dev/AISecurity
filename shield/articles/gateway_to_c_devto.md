---
title: "Why I Replaced My Go Gateway with 600 Lines of C"
published: false
description: "A solo developer's journey from polyglot chaos to unified C codebase. Why less really is more in AI security infrastructure."
tags: c, go, architecture, performance
cover_image:
canonical_url:
---

## The Problem: Three Languages, One Brain

I'm building [SENTINEL](https://github.com/DmitrL-dev/AISecurity) — an open-source AI security platform. Six months ago, my architecture looked like this:

```
User → Go Gateway → Python Brain (209 ML engines) → LLM
           ↓               ↑
      C Shield (DMZ)    IMMUNE (XDR monitoring)
                           ↑
                    Strike (Red Team payloads)
```

**Three languages. Three runtimes. Three deployment nightmares.**

- **Go Gateway** (400 LOC): HTTP routing, auth, rate limiting
- **Python Brain** (98K LOC): 209 detection engines, gRPC server
- **C Shield** (23K LOC): DMZ, 21 protocols, sub-ms latency
- **IMMUNE** (Python): XDR/EDR/MDR monitoring
- **Strike** (Python): Red team payloads, 39K+ attack vectors

The Go Gateway was the weakest link. It did exactly what Shield could do, but:

- Required Go runtime (~100MB)
- Added 3-5ms latency
- Needed separate deployment
- Duplicated auth/ratelimit logic

## The Question That Changed Everything

> "Who handles request routing?"

I stared at my architecture diagram. Shield already had:

- HTTP server with routing (`api_add_route()`)
- `/evaluate` endpoint for security checks
- SBP protocol to talk to Brain
- Auth via SZAA protocol

**The Gateway was a $0 cost center with 100% overlap.**

## The Decision: Kill the Gateway

```diff
- User → Go Gateway → Python Brain → LLM
+ User → C Shield → Python Brain → LLM
```

One less language. One less runtime. One less thing to break at 3 AM.

## What I Built: SLLM Protocol

600 lines of C that replaced 400 lines of Go:

```c
// include/protocols/sllm.h
shield_err_t sllm_proxy_request(
    const sllm_request_t *request,
    sllm_response_t *response
);
```

The flow:

```
1. User POST /proxy {"messages": [...]}
2. INGRESS: sllm_analyze_ingress() → Brain gRPC
3. FORWARD: sllm_forward_to_llm() → OpenAI/Gemini/Anthropic
4. EGRESS: sllm_analyze_egress() → Brain gRPC
5. Return sanitized response
```

### Multi-Provider Support

```c
typedef enum {
    SLLM_PROVIDER_OPENAI,
    SLLM_PROVIDER_GEMINI,
    SLLM_PROVIDER_ANTHROPIC,
    SLLM_PROVIDER_OLLAMA,
    SLLM_PROVIDER_CUSTOM
} sllm_provider_t;
```

Each provider has its own request/response format:

```c
// OpenAI: {"model": "gpt-4", "messages": [...]}
sllm_build_openai_body(&req, &body, &len);

// Gemini: {"contents": [{"parts": [...]}]}
sllm_build_gemini_body(&req, &body, &len);

// Anthropic: {"model": "claude-3", "messages": [...]}
sllm_build_anthropic_body(&req, &body, &len);
```

## The Numbers

| Metric            | Go Gateway | C Shield   |
| ----------------- | ---------- | ---------- |
| Lines of Code     | 400        | 600 (+50%) |
| Runtime Size      | ~100MB     | 0          |
| Latency           | 3-5ms      | <1ms       |
| Dependencies      | Go modules | Zero       |
| Deploy Complexity | Separate   | Integrated |

**Net result**: +200 LOC, -100MB, -4ms, -1 deployment target.

## The Hard Parts

### 1. HTTP in Pure C

No curl. No libraries. Just sockets:

```c
static shield_err_t http_post(
    const char *host, int port, const char *path,
    const char *headers, const char *body,
    char **response, size_t *response_len
) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    // ... 80 lines of socket code
}
```

Is it pretty? No. Does it work? Yes. Does it add dependencies? No.

### 2. JSON Without Libraries

```c
static char *extract_json_string(const char *json, const char *key) {
    char pattern[128];
    snprintf(pattern, sizeof(pattern), "\"%s\":\"", key);
    const char *start = strstr(json, pattern);
    // ... manual parsing
}
```

Could I use cJSON? Sure. But that's a dependency. Shield's philosophy: **zero runtime deps**.

### 3. Graceful Degradation

```c
if (!g_sllm_config.brain_endpoint[0]) {
    // Brain unavailable - default allow
    analysis->allowed = true;
    return SHIELD_OK;
}
```

If Brain is down, Shield doesn't crash. It logs and allows (configurable).

## What I Learned

### 1. Polyglot is Expensive

Every language is:

- A runtime to deploy
- A toolchain to maintain
- A context switch for your brain
- A potential version conflict

For a solo developer, this compounds fast.

### 2. C is Underrated for Infrastructure

Modern C (C11+) with good practices is:

- Fast (no GC pauses)
- Portable (runs everywhere)
- Debuggable (no runtime magic)
- Stable (APIs don't break yearly)

### 3. "Rewrite in Rust" Isn't Always the Answer

Rust is great. But for a project with 23K lines of working C, adding Rust means:

- New toolchain
- FFI complexity
- Mixed memory models

Sometimes the answer is: **make the C better**.

## The New Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            SENTINEL PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         🐝 HIVE (Central Core)                         │ │
│  │           Threat Intelligence • Orchestration • Policies              │ │
│  │      ThreatHunter • Watchdog • PQC • QRNG • Cognitive Signatures      │ │
│  └────────────┬──────────────────────┬──────────────────────┬────────────┘ │
│               │                      │                      │              │
│               ▼                      ▼                      ▼              │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐   │
│  │   🛡️ SHIELD (C)    │  │   🧠 BRAIN (Py)    │  │   🔴 STRIKE (Py)   │   │
│  │   DMZ / Pre-Filter │  │   ML/AI Engines    │  │   Red Team         │   │
│  │   21 Protocols     │◄─┤   209 Detectors    │──┤   39K+ Payloads    │   │
│  │   <1ms Latency     │  │   98K LOC          │  │   Crucible CTF     │   │
│  └─────────┬──────────┘  └────────────────────┘  └────────────────────┘   │
│            │                                                               │
│            │ SLLM Protocol (NEW)                                           │
│            ▼                                                               │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                     🌐 EXTERNAL AI SYSTEMS                          │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │   │ OpenAI   │  │ Gemini   │  │ Anthropic│  │ Ollama   │          │   │
│  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘          │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                             │
│                              │ SIEM/Telemetry                              │
│  ┌───────────────────────────┴───────────────────────────────────────────┐│
│  │                    🏥 IMMUNE (EDR/XDR/MDR)                             ││
│  │         Agent System • Hive Mesh • DragonFlyBSD Hardened              ││
│  │   Kernel Modules • eBPF Monitoring • Real-time Threat Response        ││
│  └───────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Complete ecosystem:**

- **HIVE** — Central brain, orchestration, cognitive signatures
- **SHIELD** (C) — DMZ, 21 protocols, <1ms, zero deps
- **BRAIN** (Python) — 209 ML engines, 98K LOC
- **STRIKE** (Python) — Red team, 39K+ payloads
- **IMMUNE** (C/Python) — EDR/XDR/MDR, kernel-level

**Result: Zero Go. Two languages. One platform.**

## Should You Do This?

**Yes, if:**

- You're a solo dev or small team
- Your Gateway is mostly pass-through
- You already have a C codebase
- Latency matters

**No, if:**

- Your Gateway has complex business logic
- You don't know C
- Your team is productive in Go
- "If it ain't broke, don't fix it" applies

## Code

Full implementation: [SENTINEL on GitHub](https://github.com/DmitrL-dev/AISecurity)

Key files:

- `include/protocols/sllm.h` — API
- `src/protocols/sllm.c` — Implementation
- `src/api/handlers.c` — `/proxy` endpoint

---

_Building AI security infrastructure solo. 209 detection engines. Pure C DMZ. Strange Math™._

_💬 Telegram: [@DmLabincev](https://t.me/DmLabincev) • 𝕏: [@DLabintcev](https://x.com/DLabintcev)_
