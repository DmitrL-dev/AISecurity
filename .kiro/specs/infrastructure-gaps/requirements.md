# Требования: Infrastructure Gaps

## Gap Analysis Results

| Gap | Current State | Action Needed |
|-----|---------------|---------------|
| K8s YAMLs | ✅ 6 files exist (`shield/k8s/`) | Link from docs |
| API Reference | ✅ 128 lines exist (`docs/reference/api.md`) | Expand + link |
| PyPI package | ⚠️ Check status | Verify pypi.org |
| GitHub badges | ⚠️ Missing | Add to README |
| arXiv DOIs | ⚠️ Missing | Add to R&D refs |

---

## FR-1: GitHub Action Badges

**Приоритет:** Medium

**Описание:** Добавить динамические badges в README header.

**Acceptance Criteria:**
- [x] Tests badge (GitHub Actions)
- [x] Coverage badge (if available)
- [x] PyPI version badge
- [x] License badge

---

## FR-2: K8s Examples Link

**Приоритет:** Low

**Описание:** Добавить ссылку на K8s YAMLs в документацию.

**Acceptance Criteria:**
- [x] Ссылка в README SHIELD секции
- [x] Ссылка в Academy Mid-Level (K8s урок)

---

## FR-3: API Reference Enhancement

**Приоритет:** Low

**Описание:** Расширить API Reference дополнительными endpoints.

**Acceptance Criteria:**
- [ ] Добавить compliance endpoints
- [ ] Добавить requirements endpoints
- [ ] Добавить design-review endpoints

---

## FR-4: arXiv DOIs

**Приоритет:** Low

**Описание:** Добавить DOI ссылки на академические источники.

**Acceptance Criteria:**
- [ ] FlipAttack arXiv ссылка
- [ ] GateBreaker arXiv ссылка
- [ ] Policy Puppetry reference

---

## Приоритеты

| FR | Gap | Priority | Effort |
|----|-----|----------|--------|
| FR-1 | Badges | Medium | 10 мин |
| FR-2 | K8s link | Low | 5 мин |
| FR-3 | API docs | Low | 30 мин |
| FR-4 | arXiv DOIs | Low | 15 мин |

**Total:** ~1 час
