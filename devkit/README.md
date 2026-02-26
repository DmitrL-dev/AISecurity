# SENTINEL DevKit

> Agent-first development toolkit for the Sentinel ecosystem.

## What's Inside

```
devkit/
├── extension/              VS Code extension (TypeScript, 29 source files)
│   ├── src/agents/         Agent orchestration, swarm spawner, model router
│   ├── src/kanban/         Task management board
│   ├── src/qa/             QA loop automation
│   ├── src/tdd/            TDD runner integration
│   └── src/panels/         Dashboard webview panel
│
├── hooks/                  Git hooks
│   ├── pre-commit.sh       Bash (Linux/macOS)
│   ├── pre-commit.ps1      PowerShell (Windows)
│   └── pre-exec-guard.ps1  Execution guard
│
├── prompts/                AI agent prompt templates
│   ├── reviewer.md         Code reviewer agent
│   ├── fixer.md            Automated fixer agent
│   ├── security-audit.md   Security auditor agent
│   └── financial-guard.md  Financial security guard
│
├── rules/                  Agent behavior rules
│   ├── rationalizations.md TDD rationalization patterns (anti-patterns to avoid)
│   └── clawdbot-security.md Agent security rules (OWASP Agentic Top 10)
│
├── skills/                 Reusable agent skills
│   ├── agent-security/     OWASP Agentic security audit
│   ├── two-stage-review/   Spec compliance + code quality review
│   ├── qa-fix-loop/        Reviewer → Fixer automated cycle
│   └── tdd-enforcement/    TDD Iron Law enforcement
│
├── specs/                  Specification templates
│   └── dot-templates.md    DOT flowchart templates for specs
│
├── ui/                     Standalone web dashboard
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
└── memory/                 Memory system integration
    └── rlm-integration.md  RLM Memory Bridge docs
```

## VS Code Extension

Full-featured development extension with agent orchestration, kanban board, QA automation, and TDD enforcement.

```bash
cd extension
npm install
npm run build
```

Press F5 in VS Code to launch. Pre-built VSIX available at `extension/sentinel-devkit-0.1.0.vsix`.

### Extension Features

| Feature | Source | Description |
|---------|--------|-------------|
| Agent Orchestrator | `src/agents/` | Multi-agent execution with model routing |
| Swarm Mode | `src/agents/SwarmSpawner.ts` | Parallel agent spawning |
| Security Scanner | `src/agents/SecurityScannerAgent.ts` | Automated security scanning |
| Kanban Board | `src/kanban/` | Task tracking with persistence |
| QA Loop | `src/qa/` | Automated reviewer → fixer cycle |
| TDD Runner | `src/tdd/` | Test-first enforcement |
| Dashboard | `src/panels/` | Unified webview panel |

## Development Methodology

The DevKit enforces a structured development process:

```
SPECIFICATION (what to build)
    Requirements → Design → Tasks → Human Review
         ↓
IMPLEMENTATION (how to build correctly)
    TDD Iron Law: RED → GREEN → REFACTOR
    (No production code without a failing test first)
         ↓
REVIEW
    Stage 1: Spec Compliance (does it match the spec?)
    Stage 2: Code Quality (is it maintainable?)
         ↓
MERGE
```

## Agent Prompts

Pre-built prompt templates for AI coding agents:

- **reviewer.md** — Structured code review with severity levels and actionable feedback
- **fixer.md** — Automated issue resolution with minimal diff changes
- **security-audit.md** — OWASP-aligned security scanning for AI agent code
- **financial-guard.md** — Financial data protection and compliance checks

## Skills

Reusable skill definitions that can be loaded by compatible AI agents:

| Skill | Description |
|-------|-------------|
| `agent-security` | OWASP Agentic Top 10 2026 audit checklist |
| `two-stage-review` | Split review into spec compliance + code quality |
| `qa-fix-loop` | Autonomous reviewer → issue → fixer → re-review cycle |
| `tdd-enforcement` | Enforces test-first development, blocks rationalization |

## Git Hooks

Install pre-commit hooks to enforce quality gates:

```bash
# Linux/macOS
cp devkit/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Windows PowerShell
Copy-Item devkit\hooks\pre-commit.ps1 .git\hooks\pre-commit
```
