# 🔀 Lesson 4.4: PR Process

> **Time: 25 minutes** | Expert Module 4

---

## Contribution Workflow

```
Fork → Branch → Develop → Test → PR → Review → Merge
```

---

## Branch Naming

```bash
git checkout -b feat/engine-new-attack
git checkout -b fix/injection-false-positive
git checkout -b docs/tda-explanation
```

---

## Commit Messages

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

Example:
```
feat(brain): add FlipAttack detector

Implements detection for FlipAttack (arXiv:2024.12345).
20 unit tests, 95% accuracy on test set.

Closes #456
```

---

## PR Template

```markdown
## Description
[What does this PR do?]

## Related Issue
Closes #XXX

## Checklist
- [ ] Unit tests added
- [ ] All tests pass
- [ ] Code follows style guide
- [ ] OWASP mapping documented
```

---

## Review Process

1. **Automated** — CI checks pass
2. **Maintainer** — Code review
3. **Merge** — Squash and merge

---

## Next Lesson

→ [5.1: R&D Methodology](./18-rnd-methodology.md)
