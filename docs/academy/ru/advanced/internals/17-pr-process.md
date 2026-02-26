# 🔀 Урок 4.4: PR Process

> **Время: 25 минут** | Expert Module 4

---

## Contribution Workflow

```
Fork → Branch → Develop → Test → PR → Review → Merge
```

---

## Branch Naming

```bash
# Features
git checkout -b feat/engine-new-attack

# Fixes
git checkout -b fix/injection-false-positive

# Docs
git checkout -b docs/tda-explanation
```

---

## Commit Messages

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Examples:
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

## Changes
- [ ] New engine
- [ ] Bug fix
- [ ] Documentation
- [ ] Tests

## Testing
- [ ] Unit tests added
- [ ] All tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code follows style guide
- [ ] Docstrings added
- [ ] OWASP mapping documented
- [ ] Performance within budget
```

---

## Review Process

1. **Automated** — CI checks pass
2. **Maintainer** — Code review
3. **Merge** — Squash and merge

---

## Следующий урок

→ [5.1: R&D Methodology](./18-rnd-methodology.md)
