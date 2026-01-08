# IMMUNE TLS Transport — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Provide secure, encrypted communication between IMMUNE Agent and Hive components using TLS 1.3 with mutual authentication (mTLS).

### 1.2 Scope

| In Scope | Out of Scope |
|----------|--------------|
| TLS 1.3 transport | DTLS (UDP) |
| mTLS (client+server auth) | TLS 1.2 fallback |
| Certificate pinning | OCSP/CRL checks |
| Session resumption | Hardware security modules |
| wolfSSL library | OpenSSL alternative |

### 1.3 References

- [wolfSSL Documentation](https://www.wolfssl.com/documentation/)
- [RFC 8446 - TLS 1.3](https://tools.ietf.org/html/rfc8446)
- IMMUNE Architecture Critique (S1: Unencrypted TCP)

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | TLS 1.3 encryption for all Agent-Hive traffic | P0 |
| FR-02 | Server certificate verification | P0 |
| FR-03 | Client certificate authentication (mTLS) | P0 |
| FR-04 | Certificate pinning (SHA-256 hash) | P0 |
| FR-05 | Configurable certificate paths | P1 |
| FR-06 | Session resumption (performance) | P2 |
| FR-07 | Graceful connection recovery | P2 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Handshake latency | < 100ms (localhost) |
| NFR-02 | Memory footprint | < 100KB per connection |
| NFR-03 | Binary size increase | < 200KB (wolfSSL static) |
| NFR-04 | No external runtime deps | Static linking |

### 2.3 Security Requirements

| ID | Requirement |
|----|-------------|
| SR-01 | Reject TLS 1.2 and below |
| SR-02 | Use only strong cipher suites (AEAD) |
| SR-03 | Reject connection on cert pin mismatch |
| SR-04 | Zero plaintext in memory after use |
| SR-05 | Private key never leaves secure storage |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        AGENT                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │ Application │───>│ TLS Channel │───>│ TCP Socket      │  │
│  │   Layer     │    │ (wolfSSL)   │    │                 │  │
│  └─────────────┘    └─────────────┘    └────────┬────────┘  │
│                                                  │           │
└──────────────────────────────────────────────────┼───────────┘
                                                   │ TLS 1.3
┌──────────────────────────────────────────────────┼───────────┐
│                                                  │           │
│  ┌─────────────────┐    ┌─────────────┐    ┌────┴────────┐  │
│  │ TCP Socket      │───>│ TLS Context │───>│ Application │  │
│  │                 │    │ (wolfSSL)   │    │   Layer     │  │
│  └─────────────────┘    └─────────────┘    └─────────────┘  │
│                        HIVE                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 State Machine

```
          ┌──────────────────┐
          │   DISCONNECTED   │
          └────────┬─────────┘
                   │ connect()
                   ▼
          ┌──────────────────┐
          │   CONNECTING     │──────────┐
          └────────┬─────────┘          │ TCP error
                   │ TCP connected      ▼
                   ▼              ┌───────────┐
          ┌──────────────────┐   │   ERROR   │
          │   HANDSHAKE      │───│           │
          └────────┬─────────┘   └───────────┘
                   │ TLS success       ▲
                   ▼                   │
          ┌──────────────────┐         │
          │   CONNECTED      │─────────┘
          └────────┬─────────┘ TLS/verify error
                   │ close()
                   ▼
          ┌──────────────────┐
          │   DISCONNECTED   │
          └──────────────────┘
```

---

## 4. API Design

### 4.1 Data Types

```c
/* Configuration */
typedef struct {
    char ca_cert_path[256];
    char client_cert_path[256];
    char client_key_path[256];
    bool pin_enabled;
    uint8_t pinned_hash[32];
    int handshake_timeout;
    int read_timeout;
    bool verify_peer;
    bool mtls_enabled;
} tls_config_t;

/* Channel handle (opaque) */
typedef struct tls_channel tls_channel_t;

/* Error codes */
typedef enum {
    TLS_OK = 0,
    TLS_ERR_INIT = -1,
    TLS_ERR_CERT = -2,
    TLS_ERR_PIN_MISMATCH = -7,
    ...
} tls_error_t;
```

### 4.2 Client API

| Function | Description |
|----------|-------------|
| `tls_init()` | Initialize subsystem (once) |
| `tls_channel_create(config)` | Create channel with config |
| `tls_channel_connect(ch, host, port)` | Connect to server |
| `tls_send(ch, data, len)` | Send encrypted data |
| `tls_recv(ch, buf, max)` | Receive encrypted data |
| `tls_channel_close(ch)` | Close connection |
| `tls_channel_destroy(ch)` | Free resources |
| `tls_cleanup()` | Cleanup subsystem |

### 4.3 Server API

| Function | Description |
|----------|-------------|
| `tls_server_create(config)` | Create server context |
| `tls_server_accept(ctx, fd)` | Accept TLS client |
| `tls_server_destroy(ctx)` | Destroy server |

---

## 5. Certificate Configuration

### 5.1 Certificate Hierarchy

```
Root CA (self-signed)
  └── Hive Server Certificate
  └── Agent Client Certificate(s)
```

### 5.2 File Paths (Default)

| File | Agent Path | Hive Path |
|------|------------|-----------|
| CA cert | `/etc/immune/ca.crt` | `/etc/immune/ca.crt` |
| Server cert | — | `/etc/immune/hive.crt` |
| Server key | — | `/etc/immune/hive.key` |
| Client cert | `/etc/immune/agent.crt` | — |
| Client key | `/etc/immune/agent.key` | — |

### 5.3 Certificate Pinning

Pin = SHA-256 hash of server certificate DER encoding.

```c
// Calculate pin from certificate
openssl x509 -in hive.crt -outform DER | sha256sum
```

---

## 6. Implementation Plan

### Phase 1: Core TLS (2 days)
- [ ] tls_transport.h header ✅
- [ ] tls_transport.c implementation
- [ ] wolfSSL build integration (Makefile)
- [ ] Basic connect/send/recv

### Phase 2: Certificate Handling (1 day)
- [ ] Certificate loading
- [ ] Verification callback
- [ ] Pin checking
- [ ] mTLS client auth

### Phase 3: Integration (1 day)
- [ ] Modify agent/comm.c to use tls_*
- [ ] Modify hive/network.c to use tls_server_*
- [ ] Config file updates
- [ ] Certificate generation script

### Phase 4: Testing (1 day)
- [ ] Unit tests
- [ ] Integration test (agent ↔ hive)
- [ ] Error scenarios
- [ ] Performance benchmarks

---

## 7. Test Plan

### 7.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_init_cleanup` | Init and cleanup without leaks |
| `test_config_defaults` | Default config values |
| `test_connect_no_server` | Error handling on no server |
| `test_invalid_cert` | Reject invalid certificates |
| `test_pin_mismatch` | Reject on pin mismatch |
| `test_send_recv` | Basic data transfer |

### 7.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_agent_hive_handshake` | Full mTLS handshake |
| `test_message_exchange` | Send threat report over TLS |
| `test_reconnect` | Connection recovery |
| `test_session_resume` | Session ticket reuse |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| wolfSSL license (GPLv2) | Legal | Commercial license or static link |
| Binary size bloat | Deployment | Minimal wolfSSL build |
| Performance regression | Runtime | Session resumption |
| Certificate management | Operations | Auto-generation script |

---

## 9. Acceptance Criteria

- [ ] All Agent-Hive traffic encrypted with TLS 1.3
- [ ] Invalid certificates rejected
- [ ] Pin mismatch causes connection failure
- [ ] No plaintext credentials in memory
- [ ] All unit tests pass
- [ ] Handshake < 100ms on localhost

---

*Document ready for review*
