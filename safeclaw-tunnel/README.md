# SafeClaw Tunnel

Stealth proxy для AI-инфраструктуры. Обход DPI и IP-блокировок с использованием технологий уровня Strike Force.

## Возможности

- 🛡️ **uTLS** — TLS fingerprint = Chrome 120 (невидим для DPI)
- 🌐 **DoH** — DNS через HTTPS (обход DNS-фильтрации)
- 🔗 **WSS Tunnel** — трафик обёрнут в WebSocket
- ⏱️ **Gaussian Jitter** — защита от traffic analysis
- 🧦 **SOCKS5** — совместим с Telegram, curl, браузерами

## Quick Start

### Клиент (на вашем компьютере)

```bash
# Прямой режим (без relay, только DoH + stealth)
safeclaw-tunnel -listen :1080

# Через relay (полная маскировка + EU IP)
safeclaw-tunnel -listen :1080 -relay wss://your-vps.com/tunnel
```

### Настройка Telegram

```
Настройки → Данные и память → Тип прокси
  Тип: SOCKS5
  Сервер: 127.0.0.1
  Порт: 1080
```

### Relay (на VPS)

```bash
# С TLS
safeclaw-relay -listen :443 -cert cert.pem -key key.pem

# За reverse proxy (nginx/caddy)
safeclaw-relay -listen :8080
```

## Сборка

```bash
# Клиент
go build -o safeclaw-tunnel ./cmd/client/

# Relay
go build -o safeclaw-relay ./cmd/relay/
```

## Архитектура

```
[App] → [SOCKS5 :1080] → [uTLS+DoH] → [WSS] → [Relay VPS] → [Target]
                                                      ↑
                              РКН видит: Chrome → cdn
                              Target видит: EU IP
```

## Лицензия

MIT — Часть экосистемы SENTINEL AI Security.
