# SafeClaw Tunnel — Tasks

> **Компонент:** saas/safeclaw-tunnel/
> **Дата:** 2026-02-12

---

## Реализованные (MVP)

- [x] T-1: CLI с flag parsing (listen, http, relay, proxies, doh, version)
- [x] T-2: SOCKS5 server (internal/tunnel/socks5.go)
- [x] T-3: HTTP CONNECT proxy (internal/tunnel/http_proxy.go)
- [x] T-4: Direct dialer (internal/tunnel/direct.go)
- [x] T-5: Proxy rotator (internal/tunnel/proxy_rotator.go)
- [x] T-6: WSS tunnel client (internal/tunnel/wss.go)
- [x] T-7: uTLS module (internal/stealth/utls.go)
- [x] T-8: DoH resolver stub (internal/stealth/doh.go)
- [x] T-9: Gaussian jitter (internal/stealth/jitter.go)
- [x] T-10: Graceful shutdown (SIGINT/SIGTERM)
- [x] T-11: WSS relay server (cmd/relay/main.go)
- [x] T-12: Pre-built Windows binaries

## Roadmap

- [ ] T-13: Integrate DoH resolver в dialer pipeline
- [ ] T-14: Integrate uTLS в proxy connections
- [ ] T-15: Proxy health check (background goroutine)
- [ ] T-16: Metrics endpoint (Prometheus)
- [ ] T-17: Config file support (YAML)
- [ ] T-18: Linux/macOS binaries (CI cross-compilation)
- [ ] T-19: Auto-update mechanism
- [ ] T-20: Geo-routing (выбор прокси по целевому региону)
