# SENTINEL Shield Documentation

## 🚀 START HERE

**New to Shield?** Follow this path:

```
1️⃣ README.md         → What is Shield?
2️⃣ QUICKSTART.md     → Run in 5 minutes
3️⃣ Tutorial 1        → Protect your first LLM
```

---

## 📚 Documentation Map

### Getting Started

| Doc                                             | Purpose   | Time   |
| ----------------------------------------------- | --------- | ------ |
| [README](../README.md)                          | Overview  | 5 min  |
| [QUICKSTART](QUICKSTART.md)                     | First run | 5 min  |
| [Tutorial 1](tutorials/01_protect_first_llm.md) | First LLM | 15 min |

### Learn

| Doc                                               | Purpose     | Level |
| ------------------------------------------------- | ----------- | ----- |
| [Tutorial 2](tutorials/02_detect_jailbreak.md)    | Jailbreaks  | SSA   |
| [Tutorial 3](tutorials/03_output_filtering.md)    | Filtering   | SSA   |
| [Tutorial 4](tutorials/04_context_management.md)  | Context     | SSP   |
| [Tutorial 5](tutorials/05_rate_limiting.md)       | Rate limits | SSP   |
| [Tutorial 6](tutorials/06_high_availability.md)   | HA          | SSP   |
| [Tutorial 7](tutorials/07_custom_guards.md)       | Guards      | SSE   |
| [Tutorial 8](tutorials/08_pattern_engineering.md) | Patterns    | SSE   |
| [Tutorial 9](tutorials/09_monitoring.md)          | Monitoring  | SSP   |
| [Tutorial 10](tutorials/10_red_team_testing.md)   | Testing     | SRTS  |

### Reference

| Doc                               | Content       |
| --------------------------------- | ------------- |
| [API](API.md)                     | All functions |
| [CLI](CLI.md)                     | All commands  |
| [Configuration](CONFIGURATION.md) | All options   |
| [Architecture](ARCHITECTURE.md)   | Internals     |

### Deploy

| Doc                                   | Content    |
| ------------------------------------- | ---------- |
| [Deployment](DEPLOYMENT.md)           | Production |
| [Performance](PERFORMANCE.md)         | Tuning     |
| [Troubleshooting](TROUBLESHOOTING.md) | Problems   |

### Academy

| Doc                                             | Content        |
| ----------------------------------------------- | -------------- |
| [Academy](ACADEMY.md)                           | Certifications |
| [Labs](academy/LABS.md)                         | Hands-on       |
| [Exam Bank](academy/EXAM_BANK.md)               | Study          |
| [Student Handbook](academy/STUDENT_HANDBOOK.md) | Guide          |

---

## 🎯 Quick Answers

**"How do I block prompt injection?"**
→ [Tutorial 1](tutorials/01_protect_first_llm.md)

**"How do I protect secrets in output?"**
→ [Tutorial 3](tutorials/03_output_filtering.md)

**"How do I deploy to production?"**
→ [Deployment Guide](DEPLOYMENT.md)

**"How do I deploy to Kubernetes?"**
→ [K8s Manifests](../k8s/README.md)

**"How do I get certified?"**
→ [SENTINEL Academy](ACADEMY.md)

---

## 🟢 Production Status

| Metric | Value |
|--------|-------|
| **Build** | 0 errors, 0 warnings |
| **Tests** | 103/103 pass (94 CLI + 9 LLM) |
| **CI/CD** | GitHub Actions (6 jobs) |
| **Docker** | Multi-stage build |
| **Kubernetes** | 5 manifests |

```
Production Ready: ████████████████████ 100%
```

---

## 📁 Project Structure

```
shield/
├── src/                 # 125 C files (~36K LOC)
├── include/             # 77 headers
├── tests/               # 103 tests
├── k8s/                 # Kubernetes manifests
├── docs/                # This documentation
├── Makefile             # Build system
├── Dockerfile           # Production image
└── .github/workflows/   # CI/CD pipeline
```

---

_"We're small, but WE CAN help you get started."_
