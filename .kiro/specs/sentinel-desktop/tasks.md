# SENTINEL Desktop — Tasks

## Phase 1: Project Setup

- [ ] **Task 1.1**: Создать Tauri проект `sentinel-desktop/`
- [ ] **Task 1.2**: Интегрировать WinDivert (Rust bindings)
- [ ] **Task 1.3**: Базовая структура: main.rs, lib.rs

---

## Phase 2: Network Interception

- [ ] **Task 2.1**: WinDivert фильтр для AI API endpoints
- [ ] **Task 2.2**: TLS/HTTPS parsing (SNI extraction)
- [ ] **Task 2.3**: Интеграция с Brain API для анализа

---

## Phase 3: Tauri UI

- [ ] **Task 3.1**: System tray приложение
- [ ] **Task 3.2**: Dashboard: статистика трафика
- [ ] **Task 3.3**: Логи перехваченных запросов
- [ ] **Task 3.4**: Settings: endpoints, режимы

---

## Phase 4: Integration

- [ ] **Task 4.1**: Коммуникация с Brain API
- [ ] **Task 4.2**: Локальный кэш решений
- [ ] **Task 4.3**: Auto-start на Windows

---

## Features

- [ ] Перехват трафика к AI API (OpenAI, Anthropic, etc.)
- [ ] Block/Allow режимы
- [ ] Real-time статистика
- [ ] System tray с индикатором статуса
- [ ] Интеграция с SENTINEL Brain

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | Tauri 2.x |
| Backend | Rust |
| Frontend | HTML/CSS/JS (or Svelte) |
| Network | WinDivert |
| IPC | Brain API HTTP |

---

**Created:** 2026-01-10
