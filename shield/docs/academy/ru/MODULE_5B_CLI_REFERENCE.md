# SENTINEL Academy — Module 5B

## CLI Command Reference (194 Commands)

_SSA Level | Время: 3 часа_

---

## Введение

Shield CLI содержит **194 команды** в стиле Cisco IOS, организованные по категориям:

| Категория     | Команд | Описание              |
| ------------- | ------ | --------------------- |
| **show**      | 19     | Отображение состояния |
| **config**    | 28     | Конфигурация          |
| **debug**     | 28     | Отладка и диагностика |
| **ha**        | 14     | High Availability     |
| **zone/rule** | 13     | Зоны и правила        |
| **guard**     | 20     | Guards и security     |
| **policy**    | 19     | Policy Engine         |
| **extended**  | ~50    | Расширенные команды   |

---

## 5B.1 Show Commands (19)

### System Information

```
show version              # Версия и build info
show version detailed     # Расширенная информация
show uptime               # Время работы
show clock                # Системное время
show environment          # CPU, RAM, OS
```

### Configuration

```
show running-config       # Текущая конфигурация
show startup-config       # Сохраненная конфигурация
show history              # История команд
```

### Resources

```
show memory               # Использование памяти
show cpu                  # Загрузка CPU
show processes            # Активные процессы
show interfaces           # Сетевые интерфейсы
```

### Shield State

```
show zones                # Список зон
show guards               # Статус guards
show protocols            # Активные протоколы
show sessions             # Активные сессии
show alerts               # Алерты
show metrics              # Метрики
show counters             # Счетчики
show access-lists         # ACL
show logging              # Логи
show debugging            # Статус debug
show tech-support         # Полный дамп для support
show controllers          # Внутренние контроллеры
show inventory            # Инвентарь компонентов
```

---

## 5B.2 Config Commands (28)

### Basic

```
hostname <name>           # Имя устройства
enable secret <pass>      # Пароль enable
username <name> password <pass>  # Пользователь
banner motd <text>        # MOTD banner
```

### Logging

```
logging level <debug|info|warn|error>
logging console           # Вывод в консоль
logging buffered <size>   # Буфер логов
logging host <ip>         # Syslog сервер
```

### Time

```
ntp server <ip>           # NTP сервер
clock timezone <tz>       # Часовой пояс
```

### Network

```
ip domain-name <domain>   # Домен
ip name-server <ip>       # DNS сервер
```

### Security

```
service password-encryption  # Шифрование паролей
aaa authentication login <name> <method>  # AAA
snmp-server community <string> <ro|rw>
snmp-server host <ip>
```

### API

```
api enable                # Включить REST API
api port <port>           # Порт API
api token <token>         # API токен
metrics enable            # Включить /metrics
metrics port <port>       # Порт метрик
```

### Archiving

```
archive path <path>       # Путь архива
archive maximum <count>   # Макс. копий
```

### Navigation

```
end                       # Выход в exec mode
do <command>              # Выполнить exec команду
```

---

## 5B.3 Debug Commands (28)

### Component Debug

```
debug shield              # Shield core events
debug zone                # Zone events
debug rule                # Rule matching
debug guard               # Guard events
debug protocol            # Protocol messages
debug ha                  # HA events
debug all                 # Все debug
undebug all               # Выключить debug
no debug all              # То же
```

### Terminal

```
terminal monitor          # Включить мониторинг
terminal no monitor       # Выключить мониторинг
```

### Clear Commands

```
clear counters            # Сбросить счетчики
clear logging             # Очистить лог-буфер
clear statistics          # Сбросить статистику
clear sessions            # Очистить сессии
clear alerts              # Очистить алерты
clear blocklist           # Очистить blocklist
clear quarantine          # Очистить карантин
```

### System

```
reload                    # Перезагрузка
configure terminal        # Войти в config mode
configure memory          # Загрузить startup-config
```

### Copy/Write

```
copy running-config startup-config   # Сохранить
copy startup-config running-config   # Загрузить
write memory              # = copy run start
write erase               # Стереть startup
write terminal            # = show running
```

### Network Tools

```
ping <host>               # Ping
traceroute <host>         # Traceroute
```

---

## 5B.4 HA Commands (14)

### Standby

```
standby ip <virtual-ip>   # Virtual IP
standby priority <0-255>  # Приоритет
standby preempt           # Preempt enable
no standby preempt        # Preempt disable
standby timers <hello> <hold>  # Таймеры
standby authentication <key>   # Ключ
standby track <object> <decr>  # Tracking
standby name <cluster>    # Имя кластера
```

### Redundancy

```
redundancy                # Войти в redundancy mode
redundancy mode <active-standby|active-active>
```

### Failover

```
failover                  # Включить failover
no failover               # Выключить failover
failover lan interface <name>  # Интерфейс failover
ha sync start             # Принудительная синхронизация
```

---

## 5B.5 Zone/Rule Commands (13)

### Zones

```
zone <name>               # Создать/войти в зону
no zone <name>            # Удалить зону
```

#### Zone Subcommands

```
type <llm|rag|agent|tool|mcp|api>  # Тип зоны
provider <name>           # Провайдер
description <text>        # Описание
trust-level <0-10>        # Уровень доверия
shutdown                  # Отключить зону
no shutdown               # Включить зону
```

### Rules

```
shield-rule <num> <action> <direction> <zone-type> [match...]
no shield-rule <num>      # Удалить правило
access-list <num>         # Создать ACL
no access-list <num>      # Удалить ACL
apply zone <name> in <acl> [out <acl>]  # Применить ACL
```

---

## 5B.6 Guard Commands (20)

### Enable/Disable

```
guard enable <llm|rag|agent|tool|mcp|api|all>
no guard enable <type>    # Отключить guard
```

### Configuration

```
guard policy <type> <block|log|alert>
guard threshold <type> <0.0-1.0>
```

### Signatures

```
signature-set update      # Обновить базу сигнатур
signature-set category enable <cat>  # Включить категорию
```

### Canary Tokens

```
canary token add <token>  # Добавить canary
no canary token <token>   # Удалить canary
```

### Blocklist

```
blocklist ip add <ip>     # Добавить IP в blocklist
no blocklist ip <ip>      # Удалить IP
blocklist pattern add <pattern>  # Добавить паттерн
```

### Rate Limiting

```
rate-limit enable         # Включить rate limiting
rate-limit requests <count> per <seconds>  # Настроить
```

### Threat Intelligence

```
threat-intel enable       # Включить threat intel
threat-intel feed add <url>  # Добавить feed
```

### Alerting

```
alert destination <webhook|email|syslog> <target>
alert threshold <info|warn|critical>
```

### SIEM

```
siem enable               # Включить SIEM export
siem destination <host> <port>
siem format <cef|json|syslog>
```

---

## 5B.7 Policy Commands (19)

### Class Maps

```
class-map match-any <name>   # Создать class-map (OR)
class-map match-all <name>   # Создать class-map (AND)
no class-map <name>          # Удалить class-map
```

#### Match Conditions (в class-map)

```
match injection           # Prompt injection
match jailbreak           # Jailbreak attempt
match exfiltration        # Data exfiltration
match pattern <regex>     # Regex pattern
match contains <string>   # Содержит строку
match size greater-than <bytes>  # Размер >
match entropy-high        # Высокая энтропия
```

### Policy Maps

```
policy-map <name>         # Создать policy-map
no policy-map <name>      # Удалить policy-map
```

#### Policy Actions (в policy-map)

```
class <class-name>        # Добавить class
block                     # Блокировать
log                       # Логировать
alert                     # Алерт
rate-limit <pps>          # Rate limit
```

### Service Policy

```
service-policy input <policy>   # Применить на входе
service-policy output <policy>  # Применить на выходе
```

---

## Полный пример конфигурации

```
! SENTINEL Shield Configuration

hostname SENTINEL-PROD-1
enable secret $6$encrypted

! Logging
logging level info
logging host 192.168.1.100
logging buffered 8192

! API
api enable
api port 8080
api token secret-token-123

! Metrics
metrics enable
metrics port 9090

! HA
standby ip 10.0.0.100
standby priority 100
standby preempt
failover
failover lan interface eth1

! Guards
guard enable all
guard threshold llm 0.7
guard policy llm block

! Signatures
signature-set update
signature-set category enable injection
signature-set category enable jailbreak

! Zones
zone external
  type api
  provider openai
  trust-level 3
  no shutdown
!
zone internal
  type llm
  trust-level 8
!

! Class Maps
class-map match-any THREATS
  match injection
  match jailbreak
  match exfiltration
!

! Policy Maps
policy-map SECURITY-POLICY
  class THREATS
    block
    log
    alert
!

! Rules
shield-rule 10 deny inbound any match injection
shield-rule 20 permit inbound llm
shield-rule 100 permit any any

! Apply
zone external
  service-policy input SECURITY-POLICY
!

! SIEM
siem enable
siem destination splunk.company.com 514
siem format cef

end
```

---

## Навигация CLI

| Комбинация | Действие                        |
| ---------- | ------------------------------- |
| `?`        | Помощь по доступным командам    |
| `Tab`      | Автодополнение                  |
| `Ctrl+C`   | Прервать команду                |
| `Ctrl+Z`   | Выход в exec mode               |
| `exit`     | Выход из текущего режима        |
| `end`      | Выход в exec (из любого уровня) |

---

## CLI Modes

| Mode            | Prompt                 | Как войти            |
| --------------- | ---------------------- | -------------------- |
| User EXEC       | `Shield>`              | По умолчанию         |
| Privileged EXEC | `Shield#`              | `enable`             |
| Global Config   | `Shield(config)#`      | `configure terminal` |
| Zone Config     | `Shield(config-zone)#` | `zone <name>`        |
| Class-map       | `Shield(config-cmap)#` | `class-map ...`      |
| Policy-map      | `Shield(config-pmap)#` | `policy-map ...`     |

---

## Практика

### Задание 1: Базовая настройка

Настрой Shield:

- hostname: SHIELD-LAB-1
- API на порту 8080
- Logging на 192.168.1.50

### Задание 2: Security Policy

Создай политику:

- class-map для injection + jailbreak
- policy-map с block + alert
- Применить к zone external

### Задание 3: HA Configuration

Настрой HA кластер:

- Virtual IP: 10.0.0.100
- Priority: 150
- Preempt enabled
- Hello: 1s, Hold: 3s

---

## Итоги Module 5B

- **194 команды** в стиле Cisco IOS
- 7 категорий: show, config, debug, ha, zone, guard, policy
- Полноценный Policy Engine (class-map + policy-map)
- Production-ready CLI

---

_"194 команды = полный контроль над Shield."_
