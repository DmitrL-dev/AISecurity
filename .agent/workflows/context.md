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
