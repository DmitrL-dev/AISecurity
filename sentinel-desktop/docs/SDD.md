# SENTINEL Desktop — Software Design Document

## 1. Overview

**SENTINEL Desktop** — Windows приложение для защиты от угроз AI API.
Перехватывает, анализирует и защищает трафик к AI сервисам.

### Редакции

| Edition | Описание |
|---------|----------|
| **Home** | Автономная работа, встроенные движки, CDN updates |
| **Enterprise** | + Brain/Shield интеграция, policy management, telemetry |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SENTINEL Desktop                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   UI Layer  │  │  Tauri IPC  │  │   System Tray       │  │
│  │  (HTML/TS)  │◄─┤   Bridge    │  │   (Notifications)   │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────────┘  │
├──────────────────────────┼──────────────────────────────────┤
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │               Core Engine (Rust)                       │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │  │
│  │  │ Interceptor │  │   Engines   │  │  Signatures   │  │  │
│  │  │ (WinDivert) │  │  Manager    │  │    Store      │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └───────┬───────┘  │  │
│  │         │                │                  │          │  │
│  │         ▼                ▼                  ▼          │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │              Analysis Pipeline                   │  │  │
│  │  │  SNI Extract → Engine Check → Decision → Log    │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   CDN Sync  │  │  Integrity  │  │  Brain Client       │  │
│  │  (Updates)  │  │   Checker   │  │  (Enterprise only)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Components

### 3.1 Interceptor (WinDivert)
- **Цель**: Перехват TLS ClientHello, извлечение SNI
- **Режим**: SNIFF (read-only) или INTERCEPT (block capable)
- **Фильтр**: `outbound and tcp.DstPort == 443`

### 3.2 Engines Manager
Управление движками анализа с возможностью включения/отключения.

| Engine | Описание | Patterns | Performance | Default |
|--------|----------|----------|-------------|---------|
| `jailbreak` | Детекция jailbreak/prompt injection | 7 core + CDN | ⚡ <5ms | ✅ On |
| `pii` | Обнаружение PII & secrets | 12 | ⚡ <5ms | ✅ On |
| `keywords` | Фильтрация по keywords | 85 | ⚡ <5ms | ✅ On |
| `ml_deep` | ML анализ контента | - | 🐢 ~30ms | ⚠️ Off |

```rust
pub struct EngineConfig {
    pub jailbreak_enabled: bool,
    pub pii_enabled: bool,
    pub keywords_enabled: bool,
    pub ml_deep_enabled: bool,
}
```

### 3.3 Signatures Store
Локальное хранилище сигнатур с integrity verification.

```
%APPDATA%\SENTINEL\
├── signatures/
│   ├── jailbreaks.json
│   ├── keywords.json
│   ├── pii.json
│   └── manifest.json    # SHA256 hashes
├── config.json
└── logs/
```

### 3.4 CDN Sync
Обновление сигнатур из jsdelivr CDN с auto-sync при старте.

```
CDN: cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@latest/signatures/
```

**Auto-sync при старте приложения:**
- Background thread запускается в `setup()`
- Загрузка `manifest.json` и обновлённых паттернов
- Интеграция с `jailbreak.rs` через `load_patterns_from_json()`

**Алгоритм обновления:**
1. Fetch `manifest.json`
2. Compare version with local
3. If newer: download changed files
4. Verify SHA256 hashes
5. Atomic replace
6. Hot-reload patterns into engines

### 3.5 Integrity Checker
Защита от модификации локальных файлов.

```rust
pub fn verify_integrity() -> Result<(), IntegrityError> {
    let manifest = load_manifest()?;
    for file in &manifest.files {
        let hash = sha256_file(&file.path)?;
        if hash != file.expected_hash {
            return Err(IntegrityError::Corrupted(file.path.clone()));
        }
    }
    Ok(())
}
```

**При нарушении:**
1. Alert пользователя
2. Quarantine повреждённые файлы
3. Re-download from CDN

---

## 4. Data Flow

### 4.1 Request Interception

```
┌─────────┐     ┌───────────┐     ┌─────────┐     ┌──────────┐
│  App    │────►│ WinDivert │────►│ Engine  │────►│ Decision │
│(Chrome) │     │  (SNI)    │     │ Pipeline│     │Allow/Block│
└─────────┘     └───────────┘     └─────────┘     └──────────┘
                     │                                  │
                     ▼                                  ▼
              ┌─────────────┐                    ┌──────────┐
              │ Log Entry   │◄───────────────────│   UI     │
              └─────────────┘                    └──────────┘
```

### 4.2 Engine Pipeline

```rust
pub fn analyze_request(sni: &str, payload: &[u8]) -> AnalysisResult {
    let mut result = AnalysisResult::default();
    
    if config.jailbreak_enabled {
        result.jailbreak = engines::jailbreak::check(payload);
    }
    if config.pii_enabled {
        result.pii = engines::pii::check(payload);
    }
    if config.keywords_enabled {
        result.keywords = engines::keywords::check(payload);
    }
    if config.ml_deep_enabled {
        result.ml_score = engines::ml::analyze(payload);
    }
    
    result.decision = calculate_decision(&result);
    result
}
```

---

## 5. UI Sections

### 5.1 Dashboard (Главная)
- Protection status (On/Off)
- Quick stats (connections, blocked, analyzed)
- One-click enable/disable

### 5.2 Logs (Логи)
- Real-time connection log
- Filters: by app, endpoint, status
- Details panel on click

### 5.3 Statistics (Статистика)
- Connections over time
- Top endpoints
- Threat breakdown

### 5.4 Settings (Настройки)
- **Monitored Apps**: Process picker
- **Engines**: Toggle individual engines
- **Updates**: CDN sync status, manual update
- **Behavior**: 
  - ☑ Minimize to tray on close (крестик = в трей)
  - ☑ Start with Windows
  - ☑ Start minimized
- **Advanced**: WinDivert mode, logging level

---

## 6. Security

### 6.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| Signature tampering | SHA256 + manifest verification |
| Downgrade attack | Version check, refuse older |
| MITM on CDN | jsdelivr uses HTTPS + SRI |
| Memory inspection | Sensitive data not stored in memory |
| Privilege escalation | Minimal admin for WinDivert only |

### 6.2 Integrity Chain

```
GitHub (source of truth)
    ↓ (GitHub Actions)
jsdelivr CDN (distribution)
    ↓ (HTTPS + hash verify)
Local signatures store
    ↓ (startup integrity check)
Engine runtime
```

### 6.3 Self-Protection (Anti-Tamper)

Защита процесса от завершения малварью.

**Механизмы:**

| Техника | Описание |
|---------|----------|
| **Process Guard** | Мониторинг попыток убить процесс |
| **Service Mode** | Запуск как Windows Service (сложнее убить) |
| **Watchdog** | Отдельный процесс перезапускает если убит |
| **ACL Protection** | DACL на процесс (deny terminate) |
| **Driver-level** | WinDivert driver сам защищён от unload |

```rust
pub fn enable_self_protection() {
    // Set process DACL to deny PROCESS_TERMINATE
    #[cfg(windows)]
    {
        use windows::Win32::Security::*;
        // Deny terminate for non-admin
        set_process_dacl(DENY_TERMINATE);
    }
}

pub fn start_watchdog() {
    // Spawn watchdog that restarts if main killed
    std::process::Command::new("sentinel-watchdog.exe")
        .arg("--monitor")
        .arg(std::process::id().to_string())
        .spawn();
}
```

**При попытке завершения:**
1. Log event (кто пытается)
2. Alert user
3. Watchdog перезапускает
4. (Enterprise) Report to Brain

---

## 7. Proxy Module (TLS Inspection)

Production-grade анализ контента требует расшифровки TLS трафика.

### 7.1 Architecture

```
┌──────────────┐     ┌─────────────────────────┐     ┌───────────────┐
│  Application │────►│    SENTINEL Proxy       │────►│   AI API      │
│  (Browser)   │◄────│  localhost:8443         │◄────│  (OpenAI)     │
└──────────────┘     └───────────┬─────────────┘     └───────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       ▼                       │
         │  ┌─────────────────────────────────────────┐  │
         │  │           Analysis Pipeline             │  │
         │  │                                         │  │
         │  │  Request → Decrypt → Engine Check       │  │
         │  │           → Decision → Encrypt → Send   │  │
         │  │                                         │  │
         │  │  ┌─────────┐ ┌─────────┐ ┌──────────┐  │  │
         │  │  │Keywords │ │   PII   │ │Jailbreak │  │  │
         │  │  └─────────┘ └─────────┘ └──────────┘  │  │
         │  └─────────────────────────────────────────┘  │
         └───────────────────────────────────────────────┘
```

### 7.2 Components

| Component | Purpose |
|-----------|---------|
| **Proxy Server** | HTTP/HTTPS proxy на localhost |
| **CA Generator** | Создание SENTINEL Root CA |
| **Cert Store** | Динамическая генерация сертификатов |
| **Traffic Router** | WinDivert redirect в proxy |
| **Content Analyzer** | Расшифровка + Engine pipeline |

### 7.3 CA Certificate

```
%APPDATA%\SENTINEL\certs\
├── sentinel-ca.crt          # Root CA (устанавливается в систему)
├── sentinel-ca.key          # Private key (защищён)
└── cache/                   # Кешированные site certs
    ├── api.openai.com.crt
    └── ...
```

**Установка CA:**
```rust
pub fn install_ca_certificate() -> Result<()> {
    // 1. Generate self-signed CA if not exists
    let ca = generate_ca_if_needed()?;
    
    // 2. Install to Windows cert store
    install_to_windows_store(&ca)?;
    
    // 3. Prompt user to trust
    notify_user("Установлен SENTINEL Root CA для защиты");
    
    Ok(())
}
```

### 7.4 Proxy Server

```rust
pub struct ProxyServer {
    listen_addr: SocketAddr,      // localhost:8443
    ca: Arc<CertificateAuthority>,
    engine_config: EngineConfig,
}

impl ProxyServer {
    pub async fn handle_connect(&self, stream: TcpStream, host: &str) {
        // 1. Generate cert for host
        let cert = self.ca.generate_cert(host);
        
        // 2. TLS handshake with client  
        let client_tls = accept_tls(stream, cert);
        
        // 3. Connect to upstream
        let upstream = connect_tls(host);
        
        // 4. Bidirectional proxy with inspection
        proxy_with_inspection(client_tls, upstream, &self.engine_config).await;
    }
}
```

### 7.5 Traffic Redirection

WinDivert автоматически перенаправляет трафик в proxy:

```rust
// Redirect AI endpoints to local proxy
let filter = "outbound and tcp.DstPort == 443 and (
    ip.DstAddr == <resolved_ai_ips>
)";

// Modify packet destination to localhost:8443
packet.set_dst_addr("127.0.0.1");
packet.set_dst_port(8443);
```

### 7.6 Deep Inspection Flow

```
1. App connects to api.openai.com:443
2. WinDivert redirects to localhost:8443
3. SENTINEL Proxy accepts connection
4. Proxy generates cert for api.openai.com (signed by SENTINEL CA)
5. TLS handshake with app (app trusts SENTINEL CA)
6. Proxy connects to real api.openai.com:443
7. Proxy decrypts app request
8. Engine pipeline analyzes request:
   - Keywords check → jailbreak attempt?
   - PII check → leaking secrets?
   - Jailbreak DB check → known attack?
9. Decision: Allow / Block / Modify
10. If allowed: forward to OpenAI
11. Decrypt response, log, encrypt, send to app
```

---

## 8. WinDivert Per-Process Redirect — Deep Refactoring

### 8.1 Проблема

**Текущее состояние:** WinDivert INTERCEPT mode блокирует ВСЕ соединения, даже при правильном reinject.

**Симптомы:**
- Включение Deep Inspection → весь HTTPS трафик падает
- Checksum recalculation не помогает
- SNIFF mode работает, но не может модифицировать пакеты

**Причины (установленные):**
1. TCP checksum offloading — пакеты имеют invalid checksums
2. Возможный race condition между recv() и send()
3. Неправильная модификация packet address flags

### 8.2 Решение: Reflection Pattern (Streamdump Style)

**Принцип:** Вместо изменения destination IP на 127.0.0.1, используем **reflection** — меняем src/dst IP местами и flip Outbound flag.

```
Старый (неправильный) подход:
  App → api.openai.com:443
  WinDivert изменяет: dst = 127.0.0.1:8443
  Результат: ❌ BLOCKED

Новый (Reflection) подход:
  App → api.openai.com:443
  WinDivert:
    1. SWAP src ↔ dst IP
    2. Change dst_port → PROXY_PORT
    3. Set Outbound = FALSE (теперь Inbound)
  Результат: Пакет "отражается" к proxy как входящий
```

### 8.3 Three-Port Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          SENTINEL Desktop                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    WinDivert Layer                            │   │
│  │                                                               │   │
│  │  SOCKET Layer (SNIFF)     NETWORK Layer (INTERCEPT)          │   │
│  │  ─────────────────────    ────────────────────────           │   │
│  │  - CONNECT events         - Packet modification              │   │
│  │  - Map 5-tuple → PID      - Reflection routing               │   │
│  │  - Build CONNECTION_MAP   - Checksum recalculation           │   │
│  │                                                               │   │
│  └────────────────────────────────┬─────────────────────────────┘   │
│                                   │                                  │
│  ┌────────────────────────────────▼─────────────────────────────┐   │
│  │                     Port Routing                              │   │
│  │                                                               │   │
│  │  TARGET_PORT (443)  ─────►  PROXY_PORT (8443)                │   │
│  │       ▲                          │                            │   │
│  │       │                          ▼                            │   │
│  │       └──────────────────  ALT_PORT (8444)                   │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    HTTPS Proxy Server                         │   │
│  │                    127.0.0.1:8443                             │   │
│  │                                                               │   │
│  │  Accept reflected connections                                 │   │
│  │  Connect to original dest via ALT_PORT (8444)                │   │
│  │  TLS MITM inspection                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 8.4 Packet Flow (Детально)

**Step 1: App → Remote:443 (Outbound SYN)**
```
Исходный пакет:
  src_ip = 192.168.1.100, src_port = 54321
  dst_ip = 104.18.6.192,  dst_port = 443
  Outbound = TRUE

После Reflection:
  src_ip = 104.18.6.192,  src_port = 54321
  dst_ip = 192.168.1.100, dst_port = 8443  ← PROXY_PORT
  Outbound = FALSE  ← теперь Inbound

Результат: Proxy получает "входящее" соединение
```

**Step 2: Proxy → Real Server (через ALT_PORT)**
```
Proxy делает connect() к 104.18.6.192:8444

WinDivert перехватывает, изменяет:
  dst_port = 8444 → 443

Результат: Соединение уходит на реальный 443
```

**Step 3: Response → Proxy → App**
```
Ответы от сервера (src_port=443) изменяются:
  src_port = 443 → 8444

Proxy получает, обрабатывает, отправляет клиенту.

Ответ от Proxy (src_port=8443) отражается:
  src_port = 8443 → 443
  Outbound = FALSE
  
App получает ответ как будто от реального сервера.
```

### 8.5 CONNECTION_MAP Structure

```rust
/// 5-tuple to Process ID mapping
/// Key: (local_port, remote_ip, remote_port)
/// Value: (process_id, timestamp)
type ConnectionKey = (u16, Ipv4Addr, u16);
type ConnectionValue = (u32, Instant);
type ConnectionMap = HashMap<ConnectionKey, ConnectionValue>;

/// SOCKET layer populates this map
/// NETWORK layer reads to decide redirect
static CONNECTION_MAP: LazyLock<RwLock<ConnectionMap>> = ...;
```

### 8.6 NETWORK Layer Filter

```rust
// Single comprehensive filter
let filter = "tcp and (
    tcp.DstPort == 443 or tcp.SrcPort == 443 or
    tcp.DstPort == 8443 or tcp.SrcPort == 8443 or
    tcp.DstPort == 8444 or tcp.SrcPort == 8444
)";
```

### 8.7 Packet Processing Logic

```rust
fn process_packet(packet: &mut [u8], addr: &mut WinDivertAddress) {
    let (src_ip, dst_ip, src_port, dst_port) = parse_packet(packet);
    let is_outbound = addr.outbound();
    
    match (is_outbound, dst_port, src_port) {
        // Case 1: App → Remote:443
        (true, 443, _) if is_monitored(src_port) => {
            reflect_to_proxy(packet, addr);
        }
        
        // Case 2: Proxy → App (response)
        (true, _, 8443) => {
            reflect_to_client(packet, addr);
        }
        
        // Case 3: Proxy → Remote:8444
        (true, 8444, _) => {
            redirect_port(packet, 8444, 443);
        }
        
        // Case 4: Remote:443 → Proxy (response)
        (false, _, 443) => {
            redirect_port(packet, 443, 8444);
        }
        
        // Default: passthrough
        _ => {}
    }
    
    recalculate_checksums(packet);
}
```

### 8.8 Proxy Server Modifications

```rust
impl ProxyServer {
    /// Listen on PROXY_PORT (8443)
    pub async fn run(&self) {
        let listener = TcpListener::bind("0.0.0.0:8443").await?;
        
        while let Ok((stream, peer)) = listener.accept().await {
            // peer.ip содержит ОРИГИНАЛЬНЫЙ remote IP
            // (благодаря reflection)
            let original_dest = peer.ip();
            
            tokio::spawn(async move {
                self.handle_connection(stream, original_dest).await;
            });
        }
    }
    
    async fn handle_connection(&self, client: TcpStream, original_dest: IpAddr) {
        // Connect to ORIGINAL destination via ALT_PORT
        let server = TcpStream::connect((original_dest, ALT_PORT)).await?;
        
        // TLS MITM
        let client_tls = self.accept_tls(client, &original_dest.to_string()).await?;
        let server_tls = self.connect_tls(server, &original_dest.to_string()).await?;
        
        // Bidirectional proxy with inspection
        self.proxy_with_inspection(client_tls, server_tls).await;
    }
}
```

### 8.9 Race Condition Mitigation

**Проблема:** NETWORK packet может прийти ДО SOCKET event.

**Решение:**
```rust
struct PendingPacket {
    data: Vec<u8>,
    addr: WinDivertAddress,
    timestamp: Instant,
}

static PENDING_QUEUE: LazyLock<Mutex<VecDeque<PendingPacket>>> = ...;

fn process_packet(...) {
    if !CONNECTION_MAP.contains_key(&key) {
        // Queue packet, wait for SOCKET event
        PENDING_QUEUE.lock().push_back(PendingPacket {
            data: packet.to_vec(),
            addr,
            timestamp: Instant::now(),
        });
        return;
    }
    // ... normal processing
}

// In SOCKET layer, after adding to CONNECTION_MAP:
fn on_socket_connect(key, pid) {
    CONNECTION_MAP.insert(key, pid);
    
    // Process any pending packets for this connection
    process_pending_packets(&key);
}
```

### 8.10 Testing Strategy

**Unit Tests:**
```rust
#[test]
fn test_packet_reflection() {
    let mut packet = create_tcp_packet(
        "192.168.1.100", 54321,
        "104.18.6.192", 443,
    );
    let mut addr = WinDivertAddress::outbound();
    
    reflect_to_proxy(&mut packet, &mut addr);
    
    assert_eq!(get_src_ip(&packet), "104.18.6.192");
    assert_eq!(get_dst_ip(&packet), "192.168.1.100");
    assert_eq!(get_dst_port(&packet), 8443);
    assert!(!addr.outbound());
}
```

**Integration Tests:**
1. Start SENTINEL
2. Enable Deep Inspection
3. Run `curl https://api.openai.com/v1/models`
4. Verify: request goes through proxy, logs show inspection

**Manual Test Matrix:**
| Scenario | Expected | Status |
|----------|----------|--------|
| Browser HTTPS | No block | ⬜ |
| curl to AI API | Intercepted + logged | ⬜ |
| Multiple concurrent | All work | ⬜ |
| VPN active | No interference | ⬜ |
| High load | No drops | ⬜ |

### 8.11 Implementation Phases

**Phase 8.1: Foundation Refactor**
- [ ] Separate SOCKET and NETWORK layer handlers
- [ ] Implement CONNECTION_MAP with proper locking
- [ ] Add detailed logging for debugging

**Phase 8.2: Reflection Implementation**
- [ ] Implement reflect_to_proxy()
- [ ] Implement reflect_to_client()
- [ ] Implement port redirection for ALT_PORT
- [ ] Recalculate checksums correctly

**Phase 8.3: Proxy Server Update**
- [ ] Extract original destination from reflected packets
- [ ] Connect via ALT_PORT
- [ ] Update TLS handling

**Phase 8.4: Race Condition Handling**
- [ ] Implement PENDING_QUEUE
- [ ] Add timeout for stale pending packets
- [ ] Process pending on SOCKET events

**Phase 8.5: Testing & Hardening**
- [ ] Unit tests for packet manipulation
- [ ] Integration tests with curl
- [ ] Browser testing
- [ ] VPN compatibility testing

**Phase 8.6: Performance Optimization**
- [ ] Batch packet processing
- [ ] Async checksum calculation
- [ ] Connection cleanup (TTL)

---

## 9. Internationalization (i18n)

### 9.1 Supported Languages

| Code | Language | Status |
|------|----------|--------|
| `en` | English | ✅ Default |
| `ru` | Русский | 🔜 Translation |
| `zh` | 中文 | 🔜 Translation |
| `de` | Deutsch | 🔜 Translation |

### 9.2 Translation Files

```
src/locales/
├── en.json
├── ru.json
├── zh.json
└── de.json
```

**Format:**
```json
{
  "nav": {
    "home": "Главная",
    "protection": "Защита",
    "logs": "Логи",
    "statistics": "Статистика",
    "settings": "Настройки"
  },
  "engines": {
    "keywords": {
      "name": "Keywords Detection",
      "desc": "Подозрительные ключевые слова"
    }
  }
}
```

### 9.3 Language Detection

```rust
pub fn detect_language() -> Language {
    // 1. Check saved preference
    if let Some(lang) = config.language {
        return lang;
    }
    
    // 2. Check system locale
    let locale = get_system_locale(); // "ru-RU", "en-US"
    
    // 3. Map to supported language
    match locale.split('-').next() {
        Some("ru") => Language::Russian,
        Some("zh") => Language::Chinese,
        Some("de") => Language::German,
        _ => Language::English, // fallback
    }
}
```

### 9.4 UI Integration

```typescript
// Frontend i18n
import { t, setLocale } from './i18n';

// Usage
document.querySelector('.nav-text').textContent = t('nav.home');

// Language switch
document.getElementById('lang-select').onchange = (e) => {
    setLocale(e.target.value);
    reloadUI();
};
```

---

## 10. Enterprise Features

### 10.1 Brain Integration
```rust
pub async fn consult_brain(request: &AnalysisRequest) -> BrainDecision {
    let client = BrainClient::new(&config.brain_url);
    client.analyze(request).await
}
```

### 10.2 Policy Management
Centralized policies pushed from Brain:
- Blocked endpoints list
- Custom rules
- Engine configuration

### 10.3 Telemetry (Opt-in)
| Level | Data sent |
|-------|-----------|
| Off | Nothing |
| Anonymous | Stats only (no content) |
| Full | Request metadata for analysis |

---

## 11. Implementation Phases

### Phase 1: Foundation ✅
- [x] Tauri app scaffold
- [x] WinDivert integration
- [x] Basic UI (Kaspersky-style)
- [x] SNI extraction
- [x] Real-time logs

### Phase 2: Engines ✅
- [x] Keywords engine (85 patterns)
- [x] PII engine (12 patterns)
- [x] Engine settings UI (toggles)
- [ ] Jailbreak DB (CDN loading) — TODO in mod.rs

### Phase 3: Proxy Module (TLS Inspection) ✅
- [x] CA certificate generator (`proxy/ca.rs`)
- [x] Certificate store management (cache in CA)
- [x] HTTPS proxy server (`proxy/server.rs`)
- [x] Transparent proxy (`proxy/transparent_server.rs`)
- [x] Engine pipeline integration
- [x] Request/Response logging
- [x] TLS MITM with per-host cert generation
- [x] AI/non-AI traffic separation (passthrough for non-AI)

### Phase 4: CDN & Integrity
- [ ] CDN sync module
- [ ] Integrity verification (SHA256)
- [ ] Auto-update on startup
- [ ] Jailbreak DB download (39k patterns)

### Phase 5: i18n
- [ ] Translation files (en, ru, zh, de)
- [ ] Language detection
- [ ] UI language switcher

### Phase 6: Polish
- [x] System tray — implemented
- [ ] Notifications
- [ ] Installer (MSI/NSIS)
- [ ] Self-protection (anti-tamper)

### Phase 7: Enterprise
- [ ] Brain client
- [ ] Policy sync
- [ ] Telemetry module

---

## 11.5 Full NAT MITM Architecture

### Обзор

Для инспекции TLS трафика к AI API используется Full NAT MITM подход на базе mitmproxy_rs.

### Packet Flow

```
Client App → WinDivert capture → Redirector → smoltcp → Transparent Proxy
                                                                 ↓
Client App ← WinDivert inject ← smoltcp ← Transparent Proxy ← Real Server
```

### Компоненты

| Component | Purpose |
|-----------|---------|
| **Socket Layer** | SNIFF mode, PID tracking |
| **Network Layer** | Packet capture |
| **Inject Handle** | SEND_ONLY, packet reinject |
| **smoltcp Stack** | User-space TCP/IP |
| **NAT Table** | Connection tracking (port → original dst) |

### NAT Table Entry

```rust
pub struct NatEntry {
    pub local_port: u16,
    pub original_dst_ip: Ipv4Addr,
    pub original_dst_port: u16,
    pub pid: u32,
    pub process_name: String,
}
```

---

## 12. Dependencies

| Crate | Purpose |
|-------|---------|
| `tauri` | Desktop framework |
| `windivert` | Network interception (0.6.0) |
| `smoltcp` | User-space TCP/IP stack |
| `netstack-smoltcp` | High-level smoltcp API |
| `internet-packet` | Packet parsing, checksums |
| `reqwest` | HTTP client (CDN, Brain) |
| `serde` | Serialization |
| `sha2` | Integrity hashing |
| `chrono` | Timestamps |
| `tracing` | Logging |
| `futures-util` | Async utilities |

---

## 13. Internationalization (i18n)

Приложение поддерживает мультиязычный интерфейс.

### 13.1 Supported Locales

| Locale | Name | Status |
|--------|------|--------|
| `ru` | Русский | ✅ Default |
| `en` | English | ✅ |

### 13.2 Architecture

```
src/
├── i18n.ts              # i18n module
│   ├── t()              # Translate key
│   ├── setLocale()      # Switch language
│   ├── applyTranslations() # Apply to DOM
│   └── initLocale()     # Auto-detect
└── locales/
    ├── ru.json          # 90+ keys
    └── en.json          # English
```

### 13.3 Usage

```html
<!-- Static translation -->
<span data-i18n="nav.home">Главная</span>

<!-- Placeholder -->
<input data-i18n-placeholder="settings.searchPlaceholder" />
```

**Language selector** расположен в sidebar footer.

---

## 14. File Structure

```
sentinel-desktop/
├── src-tauri/
│   ├── src/
│   │   ├── lib.rs           # Main app logic
│   │   ├── interceptor.rs   # WinDivert handling
│   │   ├── proxy/           # TLS proxy module
│   │   │   ├── mod.rs
│   │   │   ├── server.rs    # HTTPS proxy server
│   │   │   ├── ca.rs        # CA certificate management
│   │   │   └── tls.rs       # TLS utilities
│   │   ├── engines/         # Detection engines
│   │   │   ├── mod.rs
│   │   │   ├── keywords.rs
│   │   │   ├── pii.rs
│   │   │   └── jailbreak.rs
│   │   ├── cdn.rs           # CDN sync
│   │   ├── integrity.rs     # Hash verification
│   │   ├── i18n.rs          # Internationalization
│   │   └── brain.rs         # Brain client (Enterprise)
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/
│   ├── main.ts              # Frontend logic
│   ├── i18n.ts              # i18n module
│   ├── styles.css           # UI styles
│   └── locales/             # Translation files
│       ├── en.json
│       └── ru.json
├── index.html
├── docs/
│   └── SDD.md               # This document
└── package.json
```

---

*Document Version: 1.4*
*Last Updated: 2026-01-15*
*Updated: Phase 5 (i18n) complete — EN/RU locales, ~44 UI elements*

