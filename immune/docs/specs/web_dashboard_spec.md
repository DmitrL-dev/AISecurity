# IMMUNE Web Dashboard — Specification

> **Version:** 1.0  
> **Date:** 2026-01-08  

---

## Overview

Lightweight web dashboard for IMMUNE Hive monitoring using htmx for reactive UI without heavy JS frameworks.

## Features

- Agent status view (connected agents, last heartbeat)
- Alert log (recent threats)
- Pattern management (view, add, remove patterns)
- Statistics (events, threats, performance)

## Technology

- **Backend:** Embedded C HTTP server (microhttpd or custom)
- **Frontend:** HTML + htmx + minimal CSS
- **No JS frameworks** — htmx handles reactivity

## API Endpoints

```
GET  /                    Dashboard home
GET  /agents              Agent status list (htmx partial)
GET  /alerts              Recent alerts (htmx partial)
GET  /stats               Statistics JSON
POST /patterns/add        Add pattern
POST /patterns/remove     Remove pattern
GET  /health              Health check
```

---

*Minimal spec for Phase 4.2*
