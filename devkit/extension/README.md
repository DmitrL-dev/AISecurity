# SENTINEL DevKit Extension

VS Code/Antigravity extension для agent-first development.

## Features

- **Dashboard Panel** — TDD status, SDD workflow, QA loop
- **Kanban Board** — Task management
- **RLM Integration** — Memory facts viewer
- **Agent Orchestration** — Multi-agent execution UI

## Installation

```bash
cd extension
npm install
npm run build
```

## Development

```bash
npm run watch
```

Press F5 in VS Code to launch Extension Development Host.

## TDD

Tests first:
```bash
npm run test:unit
```

## Structure

```
extension/
├── src/
│   ├── extension.ts          # Entry point
│   ├── panels/               # Webview providers
│   └── test/                 # Tests
├── media/
│   ├── main.js               # Webview logic
│   └── style.css             # Webview styles
└── resources/
    └── devkit-icon.svg       # Activity bar icon
```
