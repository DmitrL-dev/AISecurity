# Модуль 22: Advanced CLI — 199 команд

## Обзор

SENTINEL Shield CLI — это полнофункциональный командный интерфейс в стиле Cisco IOS. Он содержит ~199 команд для управления всеми аспектами системы безопасности.

---

## Архитектура CLI

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                         │
├───────────────┬───────────────┬───────────────┬─────────────┤
│    User       │   Privileged  │    Config     │   Zone      │
│    Mode       │     Mode      │    Mode       │   Config    │
│   shield>     │   shield#     │   (config)#   │  (zone)#    │
├───────────────┴───────────────┴───────────────┴─────────────┤
│                    Command Registration                      │
│                  cli_register_command()                      │
├─────────────────────────────────────────────────────────────┤
│                     shield_state_t                           │
│                   (Global State Backend)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Режимы CLI

| Режим | Prompt | Доступ |
|-------|--------|--------|
| User | `shield>` | Базовый просмотр |
| Privileged | `shield#` | После `enable` |
| Config | `shield(config)#` | После `configure terminal` |
| Zone | `shield(config-zone-X)#` | После `zone X` |

---

## Категории команд (~199)

### 1. Core Commands (commands.c) — 19

| Команда | Описание |
|---------|----------|
| `enable` | Вход в privileged mode |
| `disable` | Выход из privileged mode |
| `configure terminal` | Вход в config mode |
| `exit` / `end` | Выход из режима |
| `show zones` | Показать все зоны |
| `show rules` | Показать все правила |
| `show stats` | Показать статистику |
| `show config` | Показать конфигурацию |
| `show version` | Показать версию |
| `zone <name>` | Создать/войти в зону |
| `shield-rule <id>` | Создать правило |
| `apply` | Применить конфигурацию |
| `write` / `write memory` | Сохранить конфигурацию |
| `clear` | Очистить экран/статистику |
| `debug` | Режим отладки |
| `help` / `?` | Справка |

### 2. Security Commands (cmd_security.c) — 21

| Команда | Описание |
|---------|----------|
| `threat-hunter enable/disable` | ThreatHunter |
| `threat-hunter sensitivity <N>` | Чувствительность |
| `threat-hunter test "<text>"` | Тест |
| `watchdog enable/disable` | Watchdog |
| `watchdog auto-recovery` | Auto-recovery |
| `watchdog check` | Проверка здоровья |
| `cognitive enable/disable` | Cognitive Signatures |
| `cognitive test "<text>"` | Тест на когнитивные атаки |
| `pqc enable/disable` | Post-Quantum Crypto |
| `pqc test` | Self-test PQC |
| `secure-comm enable` | Secure Communication |
| `brain enable/disable` | Brain Integration |
| `brain url <URL>` | URL Brain API |

### 3. System Commands (cmd_system.c) — 44

| Команда | Описание |
|---------|----------|
| `clear screen` | Очистить экран |
| `clear stats` | Сбросить статистику |
| `copy running-config startup-config` | Сохранить конфиг |
| `copy startup-config running-config` | Загрузить конфиг |
| `terminal length <N>` | Длина терминала |
| `terminal width <N>` | Ширина терминала |
| `hostname <name>` | Имя хоста |
| `logging level <level>` | Уровень логирования |
| `ping <host>` | Ping |
| `traceroute <host>` | Traceroute |
| `nslookup <host>` | DNS lookup |
| `debug all` | Включить всю отладку |
| `debug guard <type>` | Отладка guard |
| `no debug all` | Выключить отладку |
| `config max-connections <N>` | Max connections |
| `config timeout <N>` | Timeout |
| `show running-config` | Running config |
| `show startup-config` | Startup config |
| `show version` | Версия Shield |
| `show uptime` | Uptime |
| `show memory` | Использование памяти |
| `show cpu` | Использование CPU |
| `reload` | Перезагрузка |

### 4. Network Commands (cmd_network.c) — 49

| Команда | Описание |
|---------|----------|
| `ha enable/disable` | High Availability |
| `ha mode active/standby` | Режим HA |
| `ha peer <URL>` | Peer URL |
| `ha status` | Статус HA |
| `siem enable/disable` | SIEM integration |
| `siem endpoint <URL>` | SIEM endpoint |
| `siem test` | Test SIEM connection |
| `rate-limit enable/disable` | Rate limiting |
| `rate-limit max <N>` | Max requests |
| `rate-limit window <sec>` | Time window |
| `blocklist enable/disable` | Blocklist |
| `blocklist add <IP/pattern>` | Добавить в blocklist |
| `blocklist remove <IP/pattern>` | Удалить из blocklist |
| `blocklist show` | Показать blocklist |
| `threat-intel enable/disable` | Threat intelligence |
| `threat-intel source <URL>` | TI source |
| `alerting enable/disable` | Alerting |
| `alerting webhook <URL>` | Webhook URL |
| `canary enable/disable` | Canary tokens |
| `canary create <name>` | Create canary |
| `api enable/disable` | REST API |
| `api port <N>` | API port |
| `api auth enable/disable` | API auth |

### 5. Guard Commands (cmd_guard.c) — 20

| Команда | Описание |
|---------|----------|
| `guard enable llm` | Enable LLM Guard |
| `guard enable rag` | Enable RAG Guard |
| `guard enable agent` | Enable Agent Guard |
| `guard enable tool` | Enable Tool Guard |
| `guard enable mcp` | Enable MCP Guard |
| `guard enable api` | Enable API Guard |
| `no guard enable <type>` | Disable guard |
| `show guard <type>` | Show guard status |
| `show guards` | Show all guards |

### 6. Show Commands (cmd_show.c) — 16

| Команда | Описание |
|---------|----------|
| `show threat-hunter` | ThreatHunter status |
| `show watchdog` | Watchdog status |
| `show cognitive` | Cognitive status |
| `show pqc` | PQC status |
| `show brain` | Brain status |
| `show rate-limit` | Rate limit status |
| `show blocklist` | Blocklist status |
| `show siem` | SIEM status |
| `show ha` | HA status |
| `show api` | API status |
| `show all` | All modules status |

---

## Пример сессии

```
shield> enable
Password: ******

shield# show version
SENTINEL Shield v1.2.0
Build: Jan 5, 2026 16:30
Compiler: GCC 13.2.0

shield# configure terminal
Enter configuration commands, one per line. End with 'end'.

shield(config)# hostname PROD-SHIELD-01
Hostname set to PROD-SHIELD-01

PROD-SHIELD-01(config)# threat-hunter enable
ThreatHunter enabled

PROD-SHIELD-01(config)# threat-hunter sensitivity 0.8
ThreatHunter sensitivity set to 0.80

PROD-SHIELD-01(config)# guard enable llm
LLM Guard enabled

PROD-SHIELD-01(config)# end

PROD-SHIELD-01# write memory
Building configuration...
Configuration saved to shield.conf
[OK]

PROD-SHIELD-01# show running-config
!
! SENTINEL Shield Configuration
! Generated: 2026-01-05 16:45:00
!
hostname PROD-SHIELD-01
!
threat-hunter enable
threat-hunter sensitivity 0.80
!
watchdog enable
watchdog auto-recovery
!
guard enable llm
guard enable rag
guard enable agent
guard enable tool
guard enable mcp
guard enable api
!
end
```

---

## Регистрация команд

Каждый модуль регистрирует свои команды:

```c
void register_security_commands(cli_context_t *ctx)
{
    shield_state_get();  // Init state
    
    for (int i = 0; security_commands[i].name != NULL; i++) {
        cli_register_command(ctx, &security_commands[i]);
    }
}
```

---

## Лабораторная работа LAB-220

### Цель
Освоить все категории CLI команд.

### Задание 1: Базовая навигация
```bash
shield> ?
shield> enable
shield# ?
shield# configure terminal
shield(config)# ?
shield(config)# end
```

### Задание 2: Полная конфигурация
```bash
shield# configure terminal
shield(config)# hostname MY-SHIELD
shield(config)# threat-hunter enable
shield(config)# threat-hunter sensitivity 0.7
shield(config)# watchdog enable
shield(config)# cognitive enable
shield(config)# pqc enable
shield(config)# guard enable llm
shield(config)# guard enable rag
shield(config)# rate-limit enable
shield(config)# rate-limit max 1000
shield(config)# end
shield# write memory
```

### Задание 3: Диагностика
```bash
shield# show all
shield# show stats
shield# watchdog check
shield# threat-hunter test "ignore previous"
```

---

## Вопросы для самопроверки

1. Сколько режимов в CLI Shield?
2. Как перейти из User mode в Config mode?
3. Какая команда сохраняет конфигурацию?
4. Как включить все Guards одной командой?
5. Что делает команда `copy running-config startup-config`?

---

## Заключение

Этот модуль завершает серию новых модулей Academy, добавленных для Phase 4 функционала SENTINEL Shield.

**Полный список новых модулей:**
- MODULE_17: ThreatHunter
- MODULE_18: Watchdog
- MODULE_19: Cognitive Signatures
- MODULE_20: Post-Quantum Cryptography
- MODULE_21: Shield State
- MODULE_22: Advanced CLI (этот модуль)

---

→ [Вернуться к ACADEMY.md](../../ACADEMY.md)
