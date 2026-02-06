# Geometric Semantic Guard

**Status:** Research  
**Priority:** HIGH  
**Created:** 2026-02-05

---

## Концепция

Измерять "геометрическое здоровье" embedding space вместо анализа содержания.

```
Input → Embed → Geometric Health Check:
  1. Fisher Curvature (информационная геометрия)
  2. Hyperbolic Hierarchy (иерархическая структура)
  3. Sheaf Consistency (локальная согласованность)
```

## Почему это уникально

| Vendor | Подход | Наш подход |
|--------|--------|------------|
| Lakera | Содержание промпта | **Геометрия** semantic space |
| CrowdStrike | Threat intelligence | **Математическая** структура |
| OWASP | Паттерны атак | **Топология** embedding |

## Научная база

- **Fisher Information Metric:** Largest eigenvalue = max vulnerability
- **Hyperbolic Embeddings:** Angular perturbations = semantic attacks
- **Sheaf Theory:** Local-to-global consistency для RAG

## Что уже есть в SENTINEL

- `TDAEngine` — персистентная гомология
- `SheafEngine` — sheaf-based детекция
- `BGE-M3 ONNX` — embeddings в Rust

## Следующие шаги

1. [ ] Изучить Fisher Information в контексте embeddings
2. [ ] POC: вычисление FIM для BGE-M3 embeddings
3. [ ] Эксперимент: hyperbolic projection embeddings
4. [ ] Связать с существующим SheafEngine
