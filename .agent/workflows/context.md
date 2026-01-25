---
description: Restore project context at session start
---

# Context Restoration Workflow

Use this workflow at the start of any new session to quickly understand the SENTINEL project.

> ⚠️ **MANDATORY**: Шаги 1-2 ОБЯЗАТЕЛЬНЫ к выполнению при КАЖДОМ восстановлении контекста!

## Steps

// turbo

1. Read the project context file:

```
view_file c:\AISecurity\.agent\PROJECT_CONTEXT.md
```

// turbo 2. **MANDATORY** — Read core instructions (PhD-level, InfoSec, Clean Architecture rules):

```
view_file c:\AISecurity\agent_system_prompts\core_instructions.md
```

3. Key facts to remember:

   - **Full version**: `c:\AISecurity\src\` (**121 engines**)
   - **Community version**: `sentinel-community\` (19 engines subset)
   - **Kernel Driver**: `sentinel-driver\` (WFP traffic interception)
   - **Language**: All communication in Russian
   - **Architecture**: Clean Architecture mandatory
   - **Security**: InfoSec mindset, Zero Trust
   - **Quality**: PhD-level rigor (Rule #15)
   - Owner: Dmitry Labintsev (chg@live.ru)

4. If doing engine work, check:

   - `c:\AISecurity\src\brain\engines\` for enterprise
   - `c:\AISecurity\sentinel-community\src\brain\engines\` for community

5. Key documentation:
   - `c:\AISecurity\README.md` - main technical docs
   - `c:\AISecurity\SENTINEL_WALKTHROUGH.md` - detailed walkthrough
   - `c:\AISecurity\docs\reference\engines\` - engine category docs

6. **MANDATORY** — Seed RLM with steering rules (prevents methodology amnesia):

```
// Read steering files
view_file c:\AISecurity\sentinel-community\.kiro\steering\tdd.md
view_file c:\AISecurity\sentinel-community\.kiro\steering\product.md
view_file c:\AISecurity\sentinel-community\.kiro\steering\tech.md

// Seed critical L0 facts into RLM
mcp_rlm-toolkit_rlm_add_hierarchical_fact:
  content: "TDD Iron Law: Перед ЛЮБЫМ кодом проверь есть ли тесты. Если НЕТ — создай тест ПЕРВЫМ."
  level: 0
  domain: "methodology"

mcp_rlm-toolkit_rlm_add_hierarchical_fact:
  content: "Steering files .kiro/steering/*.md обязательны к чтению при старте сессии"
  level: 0
  domain: "project"

mcp_rlm-toolkit_rlm_sync_state
```

> ✅ После этого шага `rlm_search_facts("TDD")` должен возвращать L0 правило
