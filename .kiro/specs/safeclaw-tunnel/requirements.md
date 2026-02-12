# SafeClaw Tunnel — Requirements

> **Компонент:** saas/safeclaw-tunnel/
> **Статус:** Implemented (MVP)
> **Дата:** 2026-02-12

---

## 1. Обзор

Go-нативный stealth-прокси для маршрутизации AI-трафика. Поддерживает SOCKS5 и HTTP CONNECT протоколы, ротацию upstream прокси с geo-тегами, WSS relay для обхода NAT/firewall, и stealth-технологии (uTLS, DNS-over-HTTPS, Gaussian Jitter) для invisible-режима.

---

## 2. Функциональные требования

### FR-1: Протоколы прокси

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-1.1 | SOCKS5 proxy server (default :1080) | P0 |
| FR-1.2 | HTTP CONNECT proxy server (default :8118) | P0 |
| FR-1.3 | WSS Relay client (для туннелирования через WebSocket) | P1 |
| FR-1.4 | Direct mode (без upstream прокси) | P0 |

### FR-2: Proxy Rotation

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-2.1 | Ротация upstream SOCKS5 прокси (round-robin) | P0 |
| FR-2.2 | Формат прокси: `user:pass@host:port#country` | P0 |
| FR-2.3 | Загрузка из CLI (--proxies) или файла (--proxy-file) | P0 |
| FR-2.4 | Geo-теги для выбора страны | P1 |
| FR-2.5 | Health check и удаление неработающих прокси | P2 |

### FR-3: Stealth Features

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-3.1 | uTLS (mimicry Chrome/Firefox TLS fingerprint) | P0 |
| FR-3.2 | DNS-over-HTTPS (Cloudflare) | P0 |
| FR-3.3 | Gaussian Jitter (случайные задержки для anti-detection) | P1 |

### FR-4: CLI

| ID | Флаг | Default | Описание |
|----|------|---------|----------|
| FR-4.1 | `--listen` | `:1080` | SOCKS5 адрес |
| FR-4.2 | `--http` | `:8118` | HTTP proxy адрес |
| FR-4.3 | `--relay` | (empty) | WSS relay URL |
| FR-4.4 | `--proxies` | (empty) | Comma-separated upstream прокси |
| FR-4.5 | `--proxy-file` | (empty) | Файл с прокси |
| FR-4.6 | `--doh` | `true` | DNS-over-HTTPS |
| FR-4.7 | `--version` | | Показать версию |

---

## 3. Нефункциональные требования

| ID | Требование |
|----|------------|
| NFR-1 | Graceful shutdown по SIGINT/SIGTERM |
| NFR-2 | Concurrent: обе прокси (SOCKS5 + HTTP) запускаются параллельно |
| NFR-3 | Zero external dependencies (только stdlib + golang.org/x) |
| NFR-4 | Компиляция в один бинарник (cross-platform) |
| NFR-5 | Логирование с timestamps и source file |

---

## 4. User Stories

### US-1: Direct Mode

```gherkin
GIVEN я запускаю safeclaw-tunnel без --proxies
WHEN бинарник стартует
THEN SOCKS5 слушает на :1080
AND HTTP CONNECT слушает на :8118
AND все соединения идут напрямую
```

### US-2: Proxy Rotation

```gherkin
GIVEN у меня файл proxies.txt с 5 прокси
WHEN я запускаю safeclaw-tunnel --proxy-file proxies.txt
THEN все прокси загружены и показаны в логах
AND запросы ротируются между прокси round-robin
```

### US-3: Windows System Proxy

```gherkin
GIVEN safeclaw-tunnel запущен на :8118
WHEN я настраиваю Windows System Proxy на 127.0.0.1:8118
THEN весь HTTP/HTTPS трафик идёт через tunnel
```

---

## 5. Acceptance Criteria

- [x] AC-1: SOCKS5 работает и принимает соединения
- [x] AC-2: HTTP CONNECT работает для browser proxy
- [x] AC-3: Proxy rotation из файла/CLI
- [x] AC-4: Graceful shutdown
- [x] AC-5: Banner и logging
- [ ] AC-6: uTLS integration в dialer
- [ ] AC-7: DoH resolver integration

---

## 6. Файловая структура

```
saas/safeclaw-tunnel/
├── cmd/
│   ├── client/
│   │   └── main.go           # CLI entry point
│   └── relay/
│       └── main.go           # WSS relay server
├── internal/
│   ├── stealth/
│   │   ├── utls.go           # uTLS fingerprint mimicry
│   │   ├── doh.go            # DNS-over-HTTPS resolver
│   │   └── jitter.go         # Gaussian jitter для anti-detection
│   └── tunnel/
│       ├── direct.go         # Direct dialer
│       ├── socks5.go         # SOCKS5 server
│       ├── http_proxy.go     # HTTP CONNECT proxy
│       ├── wss.go            # WebSocket tunnel client
│       └── proxy_rotator.go  # Upstream proxy rotation
├── proxies.txt               # Example proxy list
├── go.mod
├── go.sum
├── safeclaw-tunnel.exe       # Pre-built Windows binary
└── safeclaw-relay.exe        # Pre-built relay binary
```

---

## 7. Риски

| Риск | Митигация |
|------|-----------|
| uTLS fingerprint detection evolves | Обновление tls-сигнатур |
| Upstream прокси блокируются | Auto-removal + уведомление |
| Performance при высокой нагрузке | Go goroutines, zero-copy I/O |
