# Shield WebSocket — Tasks

## Phase 1: WebSocket Protocol

- [x] **Task 1.1**: Создать `shield/src/websocket/ws.h`
  - WebSocket opcodes (TEXT, BINARY, CLOSE, PING, PONG)
  - Connection states (CONNECTING, OPEN, CLOSING, CLOSED)
  - ws_frame_t, ws_conn_t, ws_server_t structs
  - Event types for broadcasting

- [x] **Task 1.2**: Создать `shield/src/websocket/ws.c`
  - ws_handshake() — SHA1 + Base64 accept key
  - ws_recv_frame() — parse frames with masking
  - ws_send_frame() — send with proper length encoding
  - ws_broadcast_text() — send to all clients
  - Event formatters for JSON

---

## Features Implemented

- [x] RFC 6455 compliant handshake
- [x] Frame parsing with extended payload lengths
- [x] XOR masking/unmasking
- [x] Client list management (thread-safe)
- [x] Broadcasting to all connected clients
- [x] Event types: detection, status, metrics

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| ws.h | ~100 LOC | ✅ |
| ws.c | ~290 LOC | ✅ |
| RFC 6455 | Compliant | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
