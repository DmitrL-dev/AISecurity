---
description: Keeping documentation synchronized and up-to-date
---

# Rule 28: Documentation Synchronization (MANDATORY)

## Critical Principle
**All documentation MUST be kept synchronized and accurate at all times.**

## What Must Be Updated
After ANY change to engines, features, or architecture:

1. **Central README** (`README.md`)
   - Engine count in header badges
   - All statistics (LOC, tests, etc.)
   - Feature descriptions

2. **Architecture** (`C:\AISecurity\docs\architecture\`)
   - `SENTINEL_MASTER_ARCHITECTURE.md` — engine counts, diagrams
   - `architecture_flow.md` — processing flow
   - `gateway_brain_separation.md` — component descriptions

3. **Reference** (`C:\AISecurity\docs\reference\`)
   - `engines.md` (RU) — complete engine list
   - `engines-en.md` (EN) — complete engine list
   - `api.md` — API documentation

4. **Guides** (`C:\AISecurity\docs\guides\`)
   - `configuration.md` / `configuration-en.md`
   - `deployment.md` / `deployment-en.md`
   - `integration.md` / `integration-en.md`

5. **Getting Started** (`C:\AISecurity\docs\getting-started\`)
   - `README.md` / `README-en.md`
   - `installation.md` / `installation-en.md`

## Bilingual Requirement
ALL documentation MUST exist in BOTH:
- **Russian (RU)** — primary language
- **English (EN)** — required for international use

Files must be named:
- `filename.md` — Russian version
- `filename-en.md` — English version

## Verification Checklist
Before completing any task that affects documentation:

- [ ] Central README updated
- [ ] All engine counts consistent across all files
- [ ] Architecture docs reflect current state
- [ ] Both RU and EN versions updated
- [ ] No references to outdated numbers

## How to Get Current Engine Count
```powershell
# Count actual engine files (exclude tests)
Get-ChildItem -Path .\src\brain\engines\*.py -Exclude test_*,__init__.py | Measure-Object | Select-Object -ExpandProperty Count
```

## Common Failure Modes
1. ❌ Updating README but not architecture docs
2. ❌ Updating RU version but not EN version
3. ❌ Using different numbers in different files
4. ❌ Forgetting to update getting-started guides

## Enforcement
This is a MANDATORY rule. Violations result in:
1. User frustration
2. Incorrect information spreading
3. Professional reputation damage

**ALWAYS verify all docs are synchronized before marking task complete.**
