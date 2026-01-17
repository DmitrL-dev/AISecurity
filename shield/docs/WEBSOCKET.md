# SENTINEL Shield WebSocket

## Overview

Shield provides RFC 6455 compliant WebSocket support for real-time event streaming.

---

## Features

- ✅ RFC 6455 compliant handshake
- ✅ Frame parsing with extended payload lengths
- ✅ XOR masking/unmasking
- ✅ Thread-safe client management
- ✅ Broadcasting to all connected clients
- ✅ Event types: detection, status, metrics

---

## API

### Server Setup

```c
#include "ws.h"

// Create WebSocket server
ws_server_t *ws = ws_server_create(8081);

// Start accepting connections
ws_server_start(ws);

// Broadcast event to all clients
ws_broadcast_text(ws, "{\"type\":\"detection\",\"threat\":\"injection\"}");
```

### Client Management

```c
// Get connected client count
int count = ws_server_client_count(ws);

// Iterate clients (thread-safe)
ws_server_foreach_client(ws, my_callback, user_data);
```

---

## WebSocket Frames

### Opcodes

| Opcode | Name | Description |
|--------|------|-------------|
| 0x1 | TEXT | UTF-8 text message |
| 0x2 | BINARY | Binary data |
| 0x8 | CLOSE | Connection close |
| 0x9 | PING | Ping request |
| 0xA | PONG | Pong response |

### Frame Structure

```c
typedef struct {
    uint8_t opcode;
    bool fin;
    bool masked;
    uint64_t payload_len;
    uint8_t mask_key[4];
    uint8_t *payload;
} ws_frame_t;
```

---

## Event Types

### Detection Event

```json
{
    "type": "detection",
    "timestamp": "2026-01-14T10:30:00Z",
    "threat_type": "injection",
    "severity": "high",
    "risk_score": 0.92,
    "input_hash": "abc123..."
}
```

### Status Event

```json
{
    "type": "status",
    "state": "active",
    "connections": 42,
    "requests_total": 15000,
    "blocked_total": 120
}
```

### Metrics Event

```json
{
    "type": "metrics",
    "cpu_usage": 45.2,
    "memory_mb": 128,
    "latency_p95_ms": 12,
    "rps": 350
}
```

---

## JavaScript Client Example

```javascript
const ws = new WebSocket('ws://shield.example.com:8081');

ws.onopen = () => {
    console.log('Connected to Shield');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'detection':
            console.warn('Threat detected:', data.threat_type);
            break;
        case 'status':
            console.log('Status update:', data);
            break;
        case 'metrics':
            updateDashboard(data);
            break;
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SHIELD_WS_PORT` | 8081 | WebSocket port |
| `SHIELD_WS_MAX_CLIENTS` | 1000 | Max connections |
| `SHIELD_WS_PING_INTERVAL` | 30 | Ping interval (sec) |

### Security

- WebSocket connections should use `wss://` (TLS) in production
- Combine with JWT authentication for secure access
- Rate limit connections per IP

---

## See Also

- [Architecture](ARCHITECTURE.md)
- [Authentication](AUTH.md)
- [API Reference](API.md)
