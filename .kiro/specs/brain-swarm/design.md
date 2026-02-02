# Phase 8: BRAIN Swarm — Design

> **Phase:** 8
> **Version:** 1.0
> **Дата:** 2026-01-30

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         BRAIN SWARM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    NATS JetStream                        │    │
│  │  Streams: swarm.register | swarm.heartbeat | threat.feed │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         │                    │                    │             │
│     ┌───▼───┐            ┌───▼───┐            ┌───▼───┐        │
│     │BRAIN-1│◄──────────►│BRAIN-2│◄──────────►│BRAIN-N│        │
│     │       │  JetStream │       │  JetStream │       │        │
│     │       │  Pub/Sub   │       │  Pub/Sub   │       │        │
│     └───┬───┘            └───┬───┘            └───┬───┘        │
│         │                    │                    │             │
│         └────────────────────┴────────────────────┘             │
│                              │                                   │
│                    ┌─────────▼─────────┐                        │
│                    │   Local Redis     │                        │
│                    │  (Per-node cache) │                        │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Design

### 2.1 SwarmNode

Represents a single BRAIN instance in the swarm.

```python
@dataclass
class SwarmNode:
    node_id: str           # UUID
    hostname: str
    port: int
    version: str           # BRAIN version
    status: NodeStatus     # online | degraded | offline
    capabilities: List[str] # ["analyze", "qwen_guard", ...]
    last_heartbeat: datetime
    registered_at: datetime
```

### 2.2 SwarmTransport (Interface)

Abstract transport layer for swarm communication.

```python
class SwarmTransport(ABC):
    @abstractmethod
    async def connect(self) -> None: ...
    
    @abstractmethod
    async def publish(self, subject: str, data: bytes) -> None: ...
    
    @abstractmethod
    async def subscribe(self, subject: str, handler: Callable) -> None: ...
    
    @abstractmethod
    async def close(self) -> None: ...
```

### 2.3 NatsTransport (Implementation)

```python
class NatsTransport(SwarmTransport):
    def __init__(self, servers: List[str]):
        self._nc: Optional[Client] = None
        self._js: Optional[JetStreamContext] = None
        self._servers = servers
    
    async def connect(self) -> None:
        self._nc = await nats.connect(servers=self._servers)
        self._js = self._nc.jetstream()
```

### 2.4 SwarmDiscovery

Handles node registration and heartbeat.

```python
class SwarmDiscovery:
    HEARTBEAT_INTERVAL = 5  # seconds
    DEAD_NODE_TIMEOUT = 30  # seconds
    
    def __init__(self, transport: SwarmTransport, node: SwarmNode):
        self._transport = transport
        self._node = node
        self._known_nodes: Dict[str, SwarmNode] = {}
    
    async def register(self) -> None:
        """Publish registration message."""
        await self._transport.publish(
            "brain.swarm.register",
            self._node.to_json().encode()
        )
    
    async def start_heartbeat(self) -> None:
        """Start heartbeat loop."""
        while True:
            await self._transport.publish(
                "brain.swarm.heartbeat",
                json.dumps({"node_id": self._node.node_id, "ts": time.time()}).encode()
            )
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
```

### 2.5 SwarmSync

State synchronization between nodes.

```python
class SwarmSync:
    def __init__(self, transport: SwarmTransport, collective: CollectiveImmunity):
        self._transport = transport
        self._collective = collective
    
    async def broadcast_patterns(self) -> None:
        """Broadcast threat patterns to swarm."""
        data = self._collective.export_for_federation()
        await self._transport.publish("brain.threat.patterns", json.dumps(data).encode())
    
    async def _on_patterns_received(self, msg) -> None:
        """Handle incoming patterns from other nodes."""
        data = json.loads(msg.data.decode())
        self._collective.import_federation_data(data)
```

---

## 3. NATS Subject Schema

| Subject | Purpose | Payload |
|---------|---------|---------|
| `brain.swarm.register` | Node registration | SwarmNode JSON |
| `brain.swarm.heartbeat` | Health check | `{node_id, ts}` |
| `brain.swarm.unregister` | Graceful shutdown | `{node_id}` |
| `brain.config.sync` | Config replication | `{engine, enabled, settings}` |
| `brain.threat.patterns` | Pattern sharing | Federation export JSON |
| `brain.events.{node_id}` | Per-node events | Event JSON |

---

## 4. Dashboard API

### GET /api/swarm/nodes
```json
{
  "nodes": [
    {
      "node_id": "brain-1",
      "hostname": "brain-1.local",
      "status": "online",
      "last_heartbeat": "2026-01-30T10:00:00Z",
      "capabilities": ["analyze", "qwen_guard"]
    }
  ],
  "total": 3,
  "online": 2,
  "offline": 1
}
```

### GET /api/swarm/stats
```json
{
  "total_analyses": 15420,
  "total_blocked": 892,
  "avg_latency_ms": 45,
  "patterns_shared": 156,
  "nodes": {
    "online": 2,
    "offline": 1
  }
}
```

---

## 5. File Structure

```
src/brain/swarm/
├── __init__.py
├── node.py           # SwarmNode dataclass
├── transport.py      # SwarmTransport interface
├── nats_transport.py # NATS implementation
├── discovery.py      # SwarmDiscovery
├── sync.py           # SwarmSync
└── manager.py        # SwarmManager (orchestrator)

dashboard/src/
├── app/api/swarm/
│   ├── nodes/route.ts
│   └── stats/route.ts
└── components/
    └── SwarmStatus.tsx
```

---

## 6. Configuration

```yaml
# config/swarm.yaml
swarm:
  enabled: true
  node_id: auto  # or explicit UUID
  
  nats:
    servers:
      - nats://localhost:4222
    tls:
      enabled: false  # true in production
      cert_file: /etc/sentinel/nats.crt
      key_file: /etc/sentinel/nats.key
  
  discovery:
    heartbeat_interval: 5
    dead_node_timeout: 30
  
  sync:
    pattern_broadcast_interval: 60
```

---

## 7. Sequence Diagrams

### Node Registration

```
BRAIN-1                NATS                  BRAIN-2
   │                     │                      │
   ├──── CONNECT ───────►│                      │
   │                     │                      │
   ├── register(node1) ─►│◄───────────────────►│
   │                     │                      │
   │◄─ existing nodes ───┤                      │
   │                     │                      │
   ├── heartbeat ───────►│────────────────────►│
   │         (every 5s)  │                      │
```

### Pattern Sharing

```
BRAIN-1                NATS                  BRAIN-2
   │                     │                      │
   │  detect_threat()    │                      │
   │  (3rd contributor)  │                      │
   │                     │                      │
   ├─ threat.patterns ──►│────────────────────►│
   │                     │                      │
   │                     │  import_federation() │
   │                     │           │          │
```

---

## 8. Error Handling

| Scenario | Behavior |
|----------|----------|
| NATS unavailable | Local mode, retry every 10s |
| Node fails mid-sync | Message redelivery (JetStream) |
| Network partition | Eventual consistency on reconnect |
| Malformed message | Log, skip, continue |
