# SENTINEL Shield Protocol Specifications

## Overview

SENTINEL Shield uses a suite of custom protocols for AI/LLM security:

| Protocol | Name                       | Purpose               |
| -------- | -------------------------- | --------------------- |
| STP      | Sentinel Transfer Protocol | Secure data transport |
| SBP      | Shield-Brain Protocol      | Brain integration     |
| ZDP      | Zone Discovery Protocol    | Auto-discovery        |

---

## STP (Sentinel Transfer Protocol)

### Purpose

Secure prompt/response transport between Shield and untrusted zones.

### Header Format (24 bytes)

| Offset | Size | Field       | Description                   |
| ------ | ---- | ----------- | ----------------------------- |
| 0      | 4    | magic       | 0x53545001 ("STP\x01")        |
| 4      | 2    | version     | Protocol version (0x0100)     |
| 6      | 2    | msg_type    | Message type                  |
| 8      | 4    | sequence    | Sequence number               |
| 12     | 4    | payload_len | Payload length                |
| 16     | 4    | zone_id     | Target zone ID                |
| 20     | 4    | flags       | Flags (encrypted, compressed) |

### Message Types

| Value | Name     | Direction               |
| ----- | -------- | ----------------------- |
| 0x01  | REQUEST  | Client → Zone           |
| 0x02  | RESPONSE | Zone → Client           |
| 0x03  | ACK      | Bidirectional           |
| 0x04  | NACK     | Bidirectional (blocked) |
| 0x10  | PING     | Health check            |
| 0x11  | PONG     | Health response         |

### Flags

| Bit | Flag       | Description           |
| --- | ---------- | --------------------- |
| 0   | ENCRYPTED  | Payload is encrypted  |
| 1   | COMPRESSED | Payload is compressed |
| 2   | URGENT     | Priority message      |
| 3   | MORE_DATA  | More data follows     |

---

## SBP (Shield-Brain Protocol)

### Purpose

Communication between Shield (C) and Brain (Python) for deep analysis.

### Header Format (32 bytes)

| Offset | Size | Field       | Description            |
| ------ | ---- | ----------- | ---------------------- |
| 0      | 4    | magic       | 0x53425001 ("SBP\x01") |
| 4      | 2    | version     | Protocol version       |
| 6      | 2    | msg_type    | Message type           |
| 8      | 4    | sequence    | Sequence number        |
| 12     | 4    | payload_len | Payload length         |
| 16     | 8    | timestamp   | Unix timestamp (ms)    |
| 24     | 4    | flags       | Flags                  |
| 28     | 4    | reserved    | Reserved               |

### Message Types

**Shield → Brain:**

| Value | Name            | Description            |
| ----- | --------------- | ---------------------- |
| 0x01  | ANALYZE_REQUEST | Request deep analysis  |
| 0x02  | THREAT_REPORT   | Report detected threat |
| 0x03  | STATS_SYNC      | Sync statistics        |

**Brain → Shield:**

| Value | Name             | Description          |
| ----- | ---------------- | -------------------- |
| 0x11  | ANALYZE_RESPONSE | Analysis result      |
| 0x12  | BLOCKLIST_UPDATE | Update blocklist     |
| 0x13  | CONFIG_UPDATE    | Update configuration |
| 0x14  | SIGNATURE_UPDATE | Update signatures    |

**Bidirectional:**

| Value | Name      | Description     |
| ----- | --------- | --------------- |
| 0x20  | HEARTBEAT | Keep-alive      |
| 0x21  | ACK       | Acknowledgement |

---

## ZDP (Zone Discovery Protocol)

### Purpose

Auto-discovery of LLM/RAG/Agent endpoints in the network.

### Transport

- UDP multicast
- Group: 239.255.255.250
- Port: 5350 (configurable)

### Header Format (16 bytes)

| Offset | Size | Field       | Description            |
| ------ | ---- | ----------- | ---------------------- |
| 0      | 4    | magic       | 0x5A445001 ("ZDP\x01") |
| 4      | 2    | version     | Protocol version       |
| 6      | 2    | msg_type    | Message type           |
| 8      | 4    | payload_len | Payload length         |
| 12     | 4    | reserved    | Reserved               |

### Message Types

| Value | Name     | Description           |
| ----- | -------- | --------------------- |
| 0x01  | ANNOUNCE | Zone announces itself |
| 0x02  | QUERY    | Query for zones       |
| 0x03  | RESPONSE | Response to query     |
| 0x04  | LEAVE    | Zone is leaving       |

### Zone Capabilities

| Bit | Capability | Description        |
| --- | ---------- | ------------------ |
| 0   | CHAT       | Chat completion    |
| 1   | COMPLETION | Text completion    |
| 2   | EMBEDDING  | Embeddings         |
| 3   | IMAGE      | Image generation   |
| 4   | AUDIO      | Audio processing   |
| 5   | TOOL_CALL  | Tool calling       |
| 6   | STREAMING  | Supports streaming |
| 7   | FUNCTION   | Function calling   |

---

## Security Considerations

1. **STP Encryption**: Use TLS or AES-256-GCM for payload
2. **SBP Authentication**: Require mutual TLS for Brain connection
3. **ZDP**: Only trusted network segments, no sensitive data

---

## Future Protocols

| Protocol | Purpose              | Priority |
| -------- | -------------------- | -------- |
| SAF      | Analytics Flow       | P2       |
| SHSP     | Hot Standby Protocol | P3       |
| SSRP     | State Replication    | P3       |
