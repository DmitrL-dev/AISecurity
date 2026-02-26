# DevKit Git Hooks

> Pre-commit hooks для автоматического enforcement DevKit правил

## Установка

### Windows (PowerShell)

```powershell
# Копировать hook в .git/hooks
Copy-Item "devkit/hooks/pre-commit.ps1" ".git/hooks/pre-commit"

# Или создать wrapper для PowerShell
@"
#!/bin/sh
powershell.exe -ExecutionPolicy Bypass -File "$(git rev-parse --show-toplevel)/devkit/hooks/pre-commit.ps1"
"@ | Out-File -FilePath ".git/hooks/pre-commit" -Encoding utf8
```

### Linux/macOS (Bash)

```bash
# Копировать и сделать executable
cp devkit/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Husky (npm projects)

```bash
npx husky add .husky/pre-commit "bash devkit/hooks/pre-commit.sh"
```

---

## Что проверяется

| Check | Severity | Описание |
|-------|----------|----------|
| TDD Iron Law | 🔴 Blocking | Нет тестов при изменении src/ |
| Debug Code | 🟡 Warning | print(), debugger, breakpoint() |
| Secrets | 🔴 Blocking | Hardcoded passwords, tokens |
| Python Syntax | 🔴 Blocking | Синтаксические ошибки |

---

## Bypass (если очень нужно)

```bash
git commit --no-verify -m "message"
```

⚠️ **НЕ РЕКОМЕНДУЕТСЯ** — используй только в крайних случаях.

---

## Кастомизация

Добавить свои проверки в конец скрипта:

```bash
# === Check N: Custom Check ===
echo "📋 Check N: My Custom Check"
# ... your logic
```

---

## Интеграция с CI

Те же проверки можно запускать в GitHub Actions:

```yaml
- name: DevKit Pre-commit Checks
  run: bash devkit/hooks/pre-commit.sh
```
