---
description: Pre-release checklist to avoid chaos
---

# Release Workflow (Avoid Chaos)

// turbo-all

## Phase 1: Code Ready (Before Merge)

### 1. Run Full Test Suite

```bash
cd src/brain/engines
pytest -v --tb=short 2>&1 | Tee-Object test_results.txt
```

- [ ] All tests pass (0 failures)
- [ ] No import errors

### 2. Check Engine Count

```bash
Get-ChildItem -Path .\src\brain\engines\*.py -Exclude "__*","test_*","conftest*" | Measure-Object | Select-Object -ExpandProperty Count
```

- [ ] Count matches README (currently 200)

### 3. Verify Imports

```bash
python -c "from src.brain import engines; print(f'Loaded: {len(dir(engines))} items')"
python -c "import strike; print('Strike OK')"
```

---

## Phase 2: Documentation Update

### 4. Update Stats in Key Files

**Metrics to sync:**

- Engines count (e.g., 200)
- Unit Tests count (e.g., 1,047)
- Lines of Code (e.g., ~81,000)
- Version (e.g., Dragon v4.0)
- Date (e.g., January 2026)
- OWASP Coverage (LLM 10/10 + ASI 10/10)

**Files to update:**

| File                                            | What to Update                     |
| ----------------------------------------------- | ---------------------------------- |
| `README.md`                                     | Engines, Tests, LOC, Version, Date |
| `docs/reference/engines-en.md`                  | Total Engines, Tests, LOC          |
| `docs/reference/engines-expert-deep-dive-en.md` | Header stats + footer              |
| `docs/reference/engines-expert-deep-dive.md`    | Same (Russian version)             |
| `docs/CHANGELOG.md`                             | Version entry, date, changes       |
| `setup.py` or `pyproject.toml`                  | Version number                     |

### 5. Add New Engines to Deep-Dive

For EACH new engine:

- [ ] Theoretical Foundation (sources)
- [ ] Implementation (code sample)
- [ ] Deviations from Theory
- [ ] Known Limitations
- [ ] Honest Assessment

### 6. Update CHANGELOG

- [ ] Add version entry with date
- [ ] List new features
- [ ] List bug fixes

---

## Phase 3: Git Operations

### 7. Commit & Push

```bash
git add -A
git commit -m "Release vX.X.X - [brief description]"
git pull --rebase origin main
git push origin main
```

### 8. Create Tag (if major release)

```bash
git tag -a vX.X.X -m "Dragon vX.X.X"
git push origin vX.X.X
```

---

## Phase 4: Social Media (PREPARE IN ADVANCE!)

### 9. X/Twitter Thread

Location: `~/.gemini/antigravity/brain/[session]/x_twitter_post.md`

Checklist:

- [ ] Each tweet < 280 chars
- [ ] Hashtags on each tweet
- [ ] GitHub link correct
- [ ] Preview image attached

### 10. Dev.to Article

Location: `~/.gemini/antigravity/brain/[session]/devto_article.md`

Checklist:

- [ ] **NO EMOJI** (copy from Notepad, not artifact viewer)
- [ ] **NO FRONTMATTER** (fill fields manually)
- [ ] Tags: add one by one, not as string
- [ ] ASCII diagrams only (no box-drawing chars)
- [ ] Test in Preview before publish

---

## Common Mistakes to Avoid

| Mistake                | Solution                   |
| ---------------------- | -------------------------- |
| Emoji break on copy    | Use ASCII-only version     |
| Tags as single string  | Add tags one by one        |
| Frontmatter not parsed | Fill title/tags manually   |
| Unicode chars corrupt  | Copy from raw file, not UI |
| ASCII art breaks       | Use simple text diagrams   |

---

## Post-Release

- [ ] Verify live post renders correctly
- [ ] Check all links work
- [ ] Monitor for engagement
- [ ] Respond to comments

---

_Last updated: January 1, 2026_
