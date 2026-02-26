# 🛡️ Исследование: Антицензура и обфускация трафика

> **Дата:** 2026-02-18
> **Контекст:** Тотальная блокировка Telegram в России с 1 апреля 2026
> **Цель:** Gap-анализ SENTINEL Strike Force vs State-of-the-Art и план усиления

---

## 1. Ландшафт угроз (февраль 2026)

### 1.1 Текущие действия РКН

| Мера | Статус | Дата |
|---|---|---|
| Блокировка YouTube (замедление) | ✅ Действует | Июль 2024 |
| Блокировка Instagram/Facebook | ✅ Тотальная | 2022 |
| Блокировка Discord, Signal | ✅ Тотальная | 2025 |
| Блокировка Cloudflare | ✅ Действует | Нач. 2025 |
| **Блокировка Telegram** | ⏳ **С 1 апреля 2026** | СМИ |
| Блокировка ECH (Encrypted Client Hello) | ✅ Действует | Ноябрь 2024 |
| Штрафы за обход блокировок | ✅ Закон | Июль 2025 |
| Запрет информации об инструментах обхода | ✅ Закон | Март 2024, 1000+ сайтов заблокировано |

### 1.2 Технологии блокировки РКН

```
┌──────────────────────────────────────────────────┐
│              ТСПУ ("Суверенный интернет")          │
│    Deep Packet Inspection на всех провайдерах     │
├──────────────────────────────────────────────────┤
│ L3: IP blacklists (реестр запрещённых)            │
│ L4: TCP fingerprinting (JA3S, p0f)               │
│ L5: TLS SNI inspection + ECH blocking            │
│ L7: HTTP header analysis, protocol detection     │
│ AI: Машинное обучение для обнаружения VPN/proxy  │
│ "Золотой Купол": ограничение 16KB на запрос      │
│ Whitelisting: мобильный интернет → белые списки   │
└──────────────────────────────────────────────────┘
```

> ⚠️ **41% пользователей в России используют VPN** (2025). РКН инвестирует в AI-фильтрацию.

---

## 2. State-of-the-Art: что работает (февраль 2026)

### 2.1 Три поколения протоколов обфускации

| Поколение | Протоколы | Принцип | Статус в России |
|---|---|---|---|
| **Gen 1: Шифрование** | Shadowsocks (legacy), obfs4 | Рандомизация пакетов | ❌ obfs4 заблокирован (июль 2025), SS заблокирован (октябрь 2024) |
| **Gen 1.5: AEAD-2022** | **Shadowsocks 2022** | BLAKE3 + AEAD + replay-защита | 🟡 Работает через обёртки (ShadowTLS, WireGuard) |
| **Gen 2: Мимикрия** | V2Ray VMess, Trojan | Маскировка под HTTPS | 🟡 Частично работает |
| **Gen 3: TLS Camouflage** | **XTLS Reality, ShadowTLS** | Кража TLS-сертификата реального сайта | ✅ **State-of-the-art** |

### 2.2 XTLS Reality — золотой стандарт (Xray-core)

```
КЛИЕНТ ──TLS1.3──→ XRAY SERVER ──Forwarding──→ apple.com (реальный)
                        │
                        ├─ ServerHello от apple.com (НАСТОЯЩИЙ!)
                        ├─ Сертификат apple.com (временная копия)
                        ├─ Подпись: X25519 ECDH + HKDF → preMasterKey
                        ├─ Для DPI: "это обычный HTTPS к apple.com"
                        └─ После handshake → VLESS proxy tunnel
```

**Ключевые техники:**
- **Certificate Stealing / Facade**: сервер отвечает сертификатом реального сайта (apple.com, microsoft.com)
- **XTLS Vision flow**: предотвращение "TLS-in-TLS" (двойное шифрование = детектируемо)
- **X25519 key exchange**: ECDH → HKDF → подпись вместо сертификата
- **Session ID manipulation**: модификация Session ID поля в TCP TLS
- **SNI whitelist bypass**: SNI = легитимный домен

### 2.3 🔑 Shadowsocks / Shadow — глубокий анализ

> **Почему Shadow:** Shadowsocks (и его обёртка Outline VPN) — **единственный протокол, который стабильно работает** через VPN-провайдеры в России на февраль 2026. Несмотря на блокировку "чистого" SS с октября 2024, комбинация SS-2022 + ShadowTLS = Gen 3 стелс.

#### 2.3.1 Эволюция протокола

```
Shadowsocks Legacy (2012)     Shadowsocks 2022 (SIP022)     SS + ShadowTLS (2024+)
        │                              │                            │
  stream cipher               AEAD-2022 (BLAKE3)            TLS Camouflage
  no replay protection         replay protection              certificate facade
  password → key               fixed-length PSK               неотличим от HTTPS
  detectable by DPI            random byte stream             ✅ РАБОТАЕТ В РОССИИ
```

#### 2.3.2 Shadowsocks 2022 (SIP022) — архитектура протокола

```
┌─────────────────────────────────────────────────────────┐
│                SHADOWSOCKS 2022 (SIP022)                │
├─────────────────────────────────────────────────────────┤
│ Шифры:                                                  │
│   • 2022-blake3-aes-128-gcm  (обязательный)            │
│   • 2022-blake3-aes-256-gcm  (обязательный)            │
│   • 2022-blake3-chacha20-poly1305 (рекомендуемый)      │
│                                                         │
│ Key Derivation:                                         │
│   PSK (фиксированная длина) → BLAKE3-KDF → session key │
│   (вместо старого HKDF_SHA1 от пароля)                 │
│                                                         │
│ Replay Protection:                                      │
│   • TCP: salt pool (60s) + timestamp window (±30s)     │
│   • UDP: session ID routing + sliding window           │
│                                                         │
│ Anti-Probing:                                           │
│   • При ошибке — НЕ закрывать сокет немедленно         │
│   • Salt + header → single write (anti-size detection)  │
│   • Трафик = random byte stream (нет сигнатур)         │
└─────────────────────────────────────────────────────────┘
```

**TCP поток (AEAD-2022):**
```
[random salt] [encrypted header (timestamp + address)] [encrypted chunks...]
     │                    │                                    │
     └── per-session key  └── BLAKE3-KDF(PSK, salt)           └── [2B len][tag][payload][tag]
                                                                   nonce++ после каждого chunk
```

**UDP пакет (AEAD-2022):**
```
[session ID] [packet ID] [encrypted payload] [tag]
      │            │              │
      └── routing  └── replay     └── AES-256-GCM / ChaCha20
                       protection
```

#### 2.3.3 SIP023 — расширяемые заголовки идентификации

```
Проблема: 1 порт = только 1 пользователь
Решение: Identity Headers (SIP023)

[Layer 0: Server PSK] → [Identity Header: hash(User1 PSK)] → [User1 data]
                       → [Identity Header: hash(User2 PSK)] → [User2 data]

• AES-блок-шифрование заголовка идентификации
• Обратная совместимость с SIP022
• 1 порт → множество пользователей с разными PSK
```

#### 2.3.4 Outline VPN (Jigsaw / Google → Outline Foundation)

| Факт | Значение |
|---|---|
| **Разработчик** | Jigsaw (подразделение Google) → Outline Foundation (янв. 2026) |
| **Протокол** | Shadowsocks (AEAD) |
| **SDK** | Outline VPN SDK (2023) — для встраивания в приложения |
| **Статус** | Передан независимому некоммерческому фонду |
| **В России** | Серверы онлайн (февраль 2026), но plain SS блокируется |
| **Ключевое** | Простой деплой, GUI для всех платформ, SDK для интеграции |

> 💡 **Стратегия Jigsaw:** "Beyond VPNs" — встраивание circumvention прямо в приложения через SDK.

#### 2.3.5 Комбо: SS-2022 + ShadowTLS = рабочая схема

```
КЛИЕНТ                     СЕРВЕР                      РЕАЛЬНЫЙ САЙТ
   │                          │                              │
   │── TLS ClientHello ──────→│── Forward ClientHello ──────→│
   │                          │                              │
   │←── TLS ServerHello ──────│←── Real Certificate ────────│
   │    (сертификат от        │    (microsoft.com)           │
   │     microsoft.com!)      │                              │
   │                          │                              │
   │══ ShadowTLS tunnel ═════→│                              │
   │   ↓                      │                              │
   │   SS-2022 (AEAD-2022)    │── Proxy to destination ─────→│ target
   │   BLAKE3 + AES-256-GCM   │                              │
   │                          │                              │
   
   DPI видит: "обычный TLS к microsoft.com" ✅
   Active probing: "да, это microsoft.com" ✅  
   Replay attack: отбит (salt pool + timestamp) ✅
```

**Почему это работает в России:**
1. **ShadowTLS** маскирует внешний слой под легитимный TLS к реальному сайту
2. **SS-2022** обеспечивает шифрованный туннель без сигнатур (random bytes)
3. **Replay protection** не даёт DPI воспроизвести перехваченные пакеты
4. **Anti-probing**: при ошибке сокет не закрывается → активный зонд не получает информации

#### 2.3.6 Блокировки и обходы: хронология

| Дата | Событие |
|---|---|
| Октябрь 2024 | РКН блокирует "чистый" Shadowsocks (и 6 других VPN-протоколов) |
| Зима 2025 | ФСБ "Операция Статика": тесты DPI-оборудования → блокировка OpenVPN, WireGuard |
| Октябрь 2024 | Mullvad оборачивает WireGuard в Shadowsocks для обфускации |
| 2025 | Мобильные провайдеры фингерпринтят полностью зашифрованные протоколы по **паттернам размеров пакетов** |
| Авг. 2025 | Upgraded SS + ShadowTLS — "blend in with normal traffic" |
| 2025 | ФСБ выделяет **60+ млрд ₽** на AI-блокировку VPN до 2027 |
| Янв. 2026 | Переход к whitelist-модели: только одобренные соединения |

#### 2.3.7 Слабости Shadowsocks (что знают цензоры)

| Вектор обнаружения | Метод | Статус |
|---|---|---|
| **Traffic fingerprinting** | Паттерны: несколько больших клиентских пакетов + частые серверные ответы | ✅ Используется мобильными ISP |
| **Active probing** | Отправка модифицированных handshake → уникальный ответ сервера | ✅ Как GFW |
| **Timing analysis** | Корреляция по времени между запросами | 🟡 Частично |
| **Entropy detection** | Высокая энтропия = зашифрованный протокол | ✅ AI-DPI |
| **Server response** | Разные ответы на валидные и невалидные пакеты | ⚡ Решено в SS-2022 |

> ⚠️ **Ключевой вывод:** "Чистый" SS детектируется и блокируется. Но **SS-2022 + ShadowTLS** (или SS + WireGuard) = рабочая комбинация.

### 2.4 Локальные DPI-bypass инструменты

| Инструмент | Принцип | Техники | Статус |
|---|---|---|---|
| **GoodbyeDPI** | Манипуляция TCP/TLS пакетов | SNI fragmentation, HTTP header manipulation | 🟡 Работает для YouTube, не для Instagram |
| **Zapret** | DNS-over-HTTPS + DPI desync | DoH + пакетная фрагментация | 🟡 Ослаблен "Золотым Куполом" (16KB лимит) |
| **ByeDPI (Android)** | Порт GoodbyeDPI на Android | TCP fragmentation | 🟡 Частично |

**DPI Bypass техники (используются в GoodbyeDPI/Zapret):**
- TLS ClientHello fragmentation (разбиение на несколько TCP-пакетов)
- TCP segmentation + TTL manipulation
- Padding extension inflation
- Tail padding (случайные пакеты перед закрытием TCP)
- Fake ACK injection

### 2.5 Универсальные платформы

| Платформа | Язык | Протоколы | Ключевое |
|---|---|---|---|
| **Sing-box** | Go | SS, VMess, VLESS, WireGuard, Trojan | Мультиплатформ, TUN, AI-routing |
| **Xray-core** | Go | VLESS+Reality, VMess, Trojan | Основа Reality |
| **Outline** | Go/TS | SS-2022, ShadowTLS | SDK для встраивания, Jigsaw/Google |
| **Hiddify** | Dart+Go | Все через Sing-box | GUI клиент для всех платформ |
| **Clash Meta (Mihomo)** | Go | SS, VMess, VLESS, Trojan, Hysteria | Rule-based routing |

### 2.6 Tor Pluggable Transports

| Transport | Статус в России | Принцип |
|---|---|---|
| **obfs4** | ❌ Заблокирован (июль 2025) | Обфускация |
| **WebTunnel** | ✅ Работает (но ограниченно) | Маскировка под HTTPS |
| **Snowflake** | 🟡 Нестабильно | Peer-to-peer через WebRTC |
| **Conjure** | 🟡 Экспериментально | Phantom hosts |

---

## 3. Gap-анализ: SENTINEL Strike Force vs State-of-the-Art

### 3.1 Наши текущие возможности (v2.3-Final)

| # | Компонент | Уровень | Файл | Статус |
|---|---|---|---|---|
| 1 | Ghost Protocol (uTLS WS) | L7 | `ghost.go` | ✅ |
| 2 | H2 Fingerprint Mimicry | L7 | `h2fingerprint.go` | ✅ |
| 3 | DoH Resolver | L7 DNS | `doh.go` | ✅ |
| 4 | TCP Fingerprint Mimicry | L4 | `tcpfp.go` | ✅ |
| 5 | TLS Session Resumption | L5 | `tlscache.go` | ✅ |
| 6 | HTTP Header Ordering | L7 | `headerorder.go` | ✅ |
| 7 | Cover Traffic | Behavioral | `cover.go` | ✅ |
| 8 | Ghost Strike (10-layer recon) | Integration | `main.go` | ✅ |

### 3.2 ❌ Чего НЕ хватает (критические GAP'ы)

| # | GAP | Приоритет | Что делают конкуренты | Impact |
|---|---|---|---|---|
| **G1** | **TLS ClientHello Fragmentation** | 🔴 CRITICAL | GoodbyeDPI, Zapret: разбиение ClientHello на 2+ TCP-пакета | Обход SNI-инспекции ТСПУ |
| **G2** | **XTLS Reality / Certificate Facade** | 🔴 CRITICAL | Xray-core: SNI и сертификат реального сайта | Полная невидимость для DPI |
| **G3** | **Shadowsocks 2022 + ShadowTLS** | 🔴 CRITICAL | SS-2022 AEAD + TLS facade = рабочая комбо в России | Проверенный рабочий протокол |
| **G4** | **VLESS Protocol** | 🟡 HIGH | Xray/Sing-box: минималистичный прокси-протокол | Нет собственного proxy protocol |
| **G5** | **ECH (Encrypted Client Hello)** | 🟡 HIGH | Firefox/Chrome: шифрование SNI | РКН блокирует ECH, но нужна поддержка |
| **G6** | **TLS Record Fragmentation** | 🟡 HIGH | Zapret: фрагментация на уровне TLS records | Дополнительный обход DPI |
| **G7** | **Multiplexing (Mux)** | 🟡 HIGH | Sing-box Sing-mux: UDP over TCP, fullcone | Один TCP = много соединений |
| **G8** | **QUIC/HTTP3 Support** | 🟡 HIGH | Hysteria, tuic: UDP-based обфускация | Альтернатива TCP-based обходу |
| **G9** | **Traffic Morphing** | 🟡 MEDIUM | Randomization размеров и таймингов | AI-resistant трафик |
| **G10** | **Domain Fronting** | 🟡 MEDIUM | Cloak: CDN fronting через major CDN | Обход IP-блокировок |
| **G11** | **Post-Quantum Key Exchange** | 🟢 LOW | Sing-box: PQ encryption support | Future-proofing |

### 3.3 Сравнительная матрица

```
                    SENTINEL    Xray-core   Sing-box    GoodbyeDPI  SS-2022+
                    Strike v2.3  +Reality                           ShadowTLS
────────────────────────────────────────────────────────────────────────────
uTLS/JA3           ✅           ✅          ✅          ❌          ❌
H2 Fingerprint     ✅           ❌          ❌          ❌          ❌
TCP Fingerprint    ✅           ❌          ❌          ⚡           ❌
Header Order       ✅           ❌          ❌          ❌          ❌
DoH                ✅           ✅          ✅          ❌          ❌
Cover Traffic      ✅           ❌          ❌          ❌          ❌
TLS Session Cache  ✅           ✅          ✅          ❌          ❌
Ghost Protocol     ✅           ❌          ❌          ❌          ❌
────────────────────────────────────────────────────────────────────────────
Reality/Cert Facade ❌          ✅✅        ✅          ❌          ✅ (via TLS)
ClientHello Frag   ❌           ❌          ❌          ✅✅        ❌
VLESS Protocol     ❌           ✅✅        ✅          ❌          ❌
Mux/Multiplex      ❌           ✅          ✅✅        ❌          ❌
QUIC/HTTP3         ❌           ✅          ✅✅        ❌          ❌
Traffic Morphing   ⚡ (jitter)  ❌          ⚡          ✅          ❌
Domain Fronting    ❌           ❌          ❌          ❌          ❌
ECH Support        ❌           ❌          ❌          ❌          ❌
────────────────────────────────────────────────────────────────────────────
SS-2022 AEAD       ❌           ❌          ✅          ❌          ✅✅
ShadowTLS          ❌           ❌          ✅          ❌          ✅✅
Replay Protection  ❌           ✅          ✅          ❌          ✅✅
Anti-Active-Probe  ✅ (Ghost)   ✅          ✅          ❌          ✅
```

> 💡 **Вывод:** SENTINEL превосходит ВСЕХ в L4-L7 fingerprint mimicry (H2, TCP, Headers, Cover Traffic). Критические GAP'ы: **протокольная обфускация** (Reality, VLESS, Mux) И **Shadowsocks-2022 + ShadowTLS** — проверенная рабочая комбо в российских условиях.

---

## 4. Roadmap усиления (по приоритетам)

### Phase 1: ClientHello Fragmentation (1-2 дня) ⭐⭐⭐

**Цель:** Обход SNI-инспекции ТСПУ без внешнего сервера

```go
// pkg/transport/chfrag.go
type ClientHelloFragmenter struct {
    FragmentSize  int   // Размер фрагмента (100-300 bytes)
    InjectFakeACK bool  // Fake ACK перед реальным
    TTLManipulate bool  // Разные TTL для фрагментов
    PaddingSize   int   // Padding extension
}

// Разбиваем ClientHello на 2+ TCP-пакета
// DPI видит только 1й фрагмент без полного SNI
func (f *ClientHelloFragmenter) Fragment(clientHello []byte) [][]byte
```

**Инспирация:** GoodbyeDPI (C), Zapret (C), ByeDPI (C)

### Phase 2: Shadowsocks 2022 Engine (2-3 дня) ⭐⭐⭐

**Цель:** Встроенный SS-2022 клиент/сервер с AEAD-2022

```go
// pkg/protocol/ss2022.go — Shadowsocks 2022 (SIP022)
type SS2022Config struct {
    // Crypto
    Cipher      string           // "2022-blake3-aes-256-gcm"
    PSK         []byte           // Fixed-length pre-shared key
    
    // Replay Protection
    SaltPool    *SaltPoolTCP     // 60s salt storage
    TimeWindow  time.Duration    // ±30s timestamp validation
    
    // SIP023: Multi-user
    IdentityPSKs map[string][]byte // user_id → PSK
}

type SS2022Stream struct {
    config   *SS2022Config
    subkey   []byte           // BLAKE3-KDF(PSK, salt) per session
    nonce    uint64           // incremented per chunk
}

// TCP: [salt][encrypted_header][chunks...]
// UDP: [session_id][packet_id][encrypted_payload][tag]
func (s *SS2022Stream) EncryptChunk(payload []byte) ([]byte, error)
func (s *SS2022Stream) DecryptChunk(cipher []byte) ([]byte, error)
```

### Phase 3: ShadowTLS Wrapper (1-2 дня) ⭐⭐⭐

**Цель:** TLS certificate facade для маскировки SS-2022

```go
// pkg/transport/shadowtls.go
type ShadowTLSDialer struct {
    TargetSite  string    // "microsoft.com", "apple.com"
    Version     int       // v3 (latest)
    Inner       net.Conn  // SS-2022 stream inside
    
    // SENTINEL уникальные улучшения:
    H2Mimicry    *H2Fingerprinter  // наш компонент
    HeaderOrder  *HeaderOrderer    // наш компонент
    TCPMimicry   *TCPFingerprinter // наш компонент
}

// Внешний слой: TLS к microsoft.com (реальный сертификат)
// Внутренний слой: SS-2022 AEAD поток
func (d *ShadowTLSDialer) Dial(ctx context.Context, addr string) (net.Conn, error)
```

> 🔥 **Уникальное преимущество:** Ни один проект не комбинирует ShadowTLS + H2 mimicry + TCP fingerprint + Header ordering. SENTINEL Shadow = самый глубокий камуфляж.

### Phase 4: TLS Record Layer Fragmentation (1 день) ⭐⭐

**Цель:** Дополнительный обход несовершенного DPI

```go  
// pkg/transport/tlsfrag.go
type TLSRecordFragmenter struct {
    MaxRecordSize int  // < 16KB (ограничение "Золотого Купола")
    SplitPosition int  // Позиция разбиения в TLS record
}
```

### Phase 5: Reality Protocol (3-5 дней) ⭐⭐⭐

**Цель:** SENTINEL-собственная реализация Reality-подобного камуфляжа

```go
// pkg/transport/reality.go
type RealityDialer struct {
    TargetSite  string // "apple.com", "microsoft.com"  
    PrivateKey  x25519.PrivateKey
    PublicKey   x25519.PublicKey
    ShortIDs    []string
    
    // Наши уникальные улучшения:
    H2Mimicry   *H2Fingerprinter   // Существующий компонент
    TCPMimicry  *TCPFingerprinter  // Существующий компонент
    CoverTraffic *CoverGenerator   // Существующий компонент
}

// Reality + H2 mimicry + TCP mimicry + Cover traffic
// = SENTINEL Reality (лучше оригинала)
```

### Phase 6: Proxy Protocol (SVLESS) (3 дня) ⭐⭐

**Цель:** Собственный proxy-протокол на базе VLESS

```go
// pkg/protocol/svless.go — SENTINEL VLESS
type SVLESSSession struct {
    UUID      uuid.UUID
    Flow      string    // "xtls-rprx-vision"
    Reality   *RealityDialer
    Mux       *Multiplexer
}
```

### Phase 7: Multiplexing + QUIC (2 дня) ⭐

**Цель:** Один TCP → много потоков; UDP обфускация

### Phase 8: SENTINEL Stealth Manager — GUI (5-7 дней) ⭐⭐⭐

**Цель:** Графическая обёртка для управления 3 профилями (Shadow, Reality, Lambda)

**Технология:** [Wails](https://wails.io/) (Go backend + WebView frontend)

**Почему Wails:**
- Backend на **Go** — весь SENTINEL уже на Go, прямая интеграция
- Frontend — HTML/CSS/JS (React/Vue) — знакомый стек
- Бинарник **~10MB** (vs Electron ~150MB, vs Tauri — Rust, не наш стек)
- System tray, нативные диалоги, hotkeys
- Кросс-платформ: Windows / macOS / Linux

```
┌─────────────────────────────────────────────────────────────┐
│  SENTINEL Stealth Manager v1.0                        ─ □ ✕ │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌────────────┐              │
│  │  Shadow   │  │  Reality  │  │   Lambda   │              │
│  │  ⚡ Fast   │  │  🛡️ Max   │  │  ♻️ Rotate │              │
│  │           │  │           │  │            │              │
│  │ SS-2022 + │  │ VLESS +   │  │ SS-2022 +  │              │
│  │ ShadowTLS │  │ Reality   │  │ Serverless │              │
│  │ + CDN     │  │ + Hop×3   │  │ + IP rot.  │              │
│  └─────┬─────┘  └─────┬─────┘  └──────┬─────┘              │
│        └──────────┬────┴───────────────┘                    │
│                   ▼                                          │
│  ┌──────────────────────────────────────────────┐           │
│  │  [● Connect]    Profile: Shadow               │           │
│  │  Status: Connected ✅  via Cloudflare CDN     │           │
│  │  Exit IP: 104.16.x.x (US)                    │           │
│  │  Latency: 47ms  ↑ 12 Mbps  ↓ 45 Mbps        │           │
│  │  DPI Bypass: ✅  IP Hidden: ✅  AI-Safe: ✅   │           │
│  └──────────────────────────────────────────────┘           │
│                                                              │
│  ⚙️ Settings  │  📊 Traffic Monitor  │  🔄 Auto-Switch     │
│  🔒 Kill Switch │  📋 Connection Log  │  🌍 Server List    │
└─────────────────────────────────────────────────────────────┘
```

```go
// cmd/stealth-manager/main.go
package main

import (
    "github.com/wailsapp/wails/v2"
    "sentinel/pkg/protocol/ss2022"
    "sentinel/pkg/transport/shadowtls"
    "sentinel/pkg/transport/reality"
)

type App struct {
    profiles map[string]*StealthProfile
    active   *StealthProfile
}

type StealthProfile struct {
    Name     string                 // "Shadow", "Reality", "Lambda"
    DPI      DPIBypassConfig        // L4-L7 mimicry settings
    Exit     IPAnonymizationConfig  // CDN / Multi-Hop / Serverless
    Morphing TrafficMorphingConfig  // Cover traffic, jitter
}

// Frontend вызывает:
func (a *App) Connect(profile string) error
func (a *App) Disconnect() error
func (a *App) GetStatus() *ConnectionStatus
func (a *App) SwitchProfile(name string) error
func (a *App) GetTrafficStats() *TrafficStats
```

**Ключевые экраны GUI:**

| Экран | Функции |
|---|---|
| **Dashboard** | Статус подключения, текущий профиль, exit IP, скорость |
| **Profiles** | Переключение Shadow/Reality/Lambda, настройка параметров |
| **Traffic** | Мониторинг трафика в реальном времени, DPI bypass статус |
| **Servers** | Список серверов/CDN endpoints, добавление своих VPS |
| **Settings** | Kill switch, auto-switch при обнаружении блокировки, логи |
| **Tray** | Быстрое Connect/Disconnect, смена профиля из трея |

### Phase 9: IP Anonymization Layer (3-4 дня) ⭐⭐

**Цель:** Интеграция Layer 2 (IP анонимизация) в каждый профиль

```go
// pkg/anonymize/chain.go
type MultiHopChain struct {
    Nodes []HopNode  // VPS-1 → VPS-2 → VPS-3
}

// pkg/anonymize/cdn.go  
type CDNProxy struct {
    Provider  string  // "cloudflare", "fastly"
    WorkerURL string  // CF Worker endpoint
    WARP      bool    // Use CF WARP
}

// pkg/anonymize/serverless.go
type ServerlessExit struct {
    Provider string  // "aws_lambda", "gcp_function", "azure_function"
    Region   string  // Auto-rotate region
}
```

---

## 5. 🎯 Проблема IP-атрибуции: "Слепая зона" всех протоколов

> ⚠️ **Критический вопрос:** Все протоколы (Reality, SS+ShadowTLS, VLESS) решают проблему **как пройти DPI**, но НЕ решают проблему **откуда выходит трафик**. Российский IP виден на exit-ноде.

### 5.1 Анатомия проблемы

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────┐
│ SENTINEL    │     │   ТСПУ / DPI     │     │   EXIT NODE   │     │  TARGET  │
│ (российский │────→│   (обход через   │────→│  (VPS в EU)   │────→│  (сайт)  │
│  IP: 95.x)  │     │    Reality/SS)   │     │  IP: 185.x    │     │          │
└─────────────┘     └──────────────────┘     └──────────────┘     └──────────┘
                           ✅                        ❌
                     DPI обойден              Но на exit-ноде
                                              мы = российский IP

ПРОБЛЕМЫ:
1. Target видит IP exit-ноды → может заблокировать VPS
2. РКН может заблокировать IP exit-ноды по blacklist
3. Exit-нода знает наш реальный IP (95.x)  
4. Логи exit-ноды = доказательство использования
5. Один VPS = single point of failure
```

### 5.2 Стратегии решения IP-анонимизации

#### Стратегия 1: CDN Proxy (Cloudflare Workers) ⭐⭐⭐

```
КЛИЕНТ → ТСПУ → Cloudflare CDN (CF IP: 104.x) → Worker → Target
                      │
                      ├─ CF видит: "WebSocket к *.workers.dev"
                      ├─ Target видит: IP Cloudflare (104.x) ← НЕ российский
                      └─ РКН НЕ может заблокировать ВСЕ IP Cloudflare
                         (миллионы легитимных сайтов на CF = collateral damage)
```

| Плюсы | Минусы |
|---|---|
| Free tier: 100K req/день | CF запрещает proxy в ToS |
| IP Cloudflare = не Россия | CF заблокирован РКН (нач. 2025) |
| Мульти-IP (CF CDN pool) | Нужен обход блокировки CF |
| Поддерживает WebSocket/VLESS | Может быть заблокирован worker endpoint |

**Статус в России:** Cloudflare IP-диапазоны частично блокируются с начала 2025. Но: WARP (1.1.1.1) бесплатный + post-quantum. Работает через alternate endpoints.

#### Стратегия 2: Multi-Hop Chain ("луковая" маршрутизация) ⭐⭐⭐

```
КЛИЕНТ → ТСПУ → VPS-1 (Финляндия) → VPS-2 (Нидерланды) → VPS-3 (Германия) → Target
                     │                      │                      │
                     └── знает клиент IP    └── знает VPS-1 IP    └── Target видит VPS-3
                         НЕ знает Target        НЕ знает клиент       НЕ знает клиент

• Каждый хоп видит только предыдущий и следующий
• Ни один VPS не знает полную цепочку
• 3+ хопа = практическая неотслеживаемость
• Latency: +50-150ms на каждый хоп
```

| Кол-во хопов | Анонимность | Скорость | Применение |
|---|---|---|---|
| 1 hop | Низкая | Быстро | Обычный VPN |
| 2 hops | Средняя | Средне | Обход IP-бана |
| **3 hops** | **Высокая** | **Медленнее** | **Рекомендуемо** |
| 4+ hops (Tor) | Максимальная | Медленно | Критические операции |

#### Стратегия 3: Serverless Functions (Lambda/Cloud Functions) ⭐⭐

```
КЛИЕНТ → ТСПУ → AWS Lambda (IP: случайный из пула Amazon)
                  → Google Cloud Function (IP: случайный из пула Google)
                  → Azure Function (IP: случайный из пула Microsoft)

Ключевое: IP РОТИРУЕТСЯ при каждом вызове!
• Нельзя заблокировать — миллионы IP
• Каждый запрос = новый IP
• $0.0000002 за запрос (бесплатный tier: ~1M/месяц)
```

#### Стратегия 4: Refraction Networking (TapDance/Conjure) ⭐⭐⭐

```
КЛИЕНТ → ТСПУ → ISP (с установленной "станцией") → Target
                      │
                      └── "Станция" встроена в ISP!
                          Перехватывает пакеты, инжектирует proxy
                          Для DPI: "обычный трафик к легитимному сайту"
                          Блокировка невозможна без блокировки ISP

TapDance: ISP-scale deployment, Psiphon использует (100K+ users/month)
Conjure: phantom proxies в неиспользуемом IP пространстве ISP
```

| Технология | Принцип | Статус | Проблема |
|---|---|---|---|
| **TapDance** | Станции на ISP uplinks | ✅ В продакшене (Psiphon) | Нужны дружественные ISP |
| **Conjure** | Phantom hosts в IP space ISP | ✅ Тестируется (Tor Alpha) | Нет ISP в России |
| **Refractive** | Univ. Michigan research | 🟡 Исследование (2025) | Академический |

> 💡 **Инсайт:** Refraction networking = **единственная** технология, которую **невозможно заблокировать** без отключения целого ISP. Но требует кооперации ISP за пределами юрисдикции цензора.

#### Стратегия 5: P2P Networks (Snowflake, I2P, Nym) ⭐

```
КЛИЕНТ → ТСПУ → Volunteer Browser 1 (WebRTC)
                → Volunteer Browser 2 (WebRTC) 
                → Volunteer Browser 3 (WebRTC) → Target

IP клиента скрыт за волонтёрскими браузерами
Миллионы IP, блокировка невозможна
Но: медленно + нестабильно в России
```

#### Стратегия 6: Residential Proxy Networks ⭐⭐

```
КЛИЕНТ → ТСПУ → Residential IP (191.x, Бразилия — реальный домашний IP)
                                                  → Target

Target видит: обычного домашнего пользователя
Не VPS, не датацентр → не заблокирован
Цена: $5-15 за 1GB через residential
```

### 5.3 ⚡ Рекомендуемая архитектура SENTINEL

```
┌─────────────────────────────────────────────────────────────────────┐
│              SENTINEL IP Anonymization Stack                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Layer 1: DPI Bypass (уже есть + roadmap Phase 1-7)                │
│  ├── ClientHello Fragmentation                                      │
│  ├── Reality / ShadowTLS Certificate Facade                         │
│  └── SS-2022 AEAD + Cover Traffic                                   │
│                                                                     │
│  Layer 2: IP Anonymization (НОВОЕ)                                  │
│  ├── [Primary]   CDN Proxy: CF Workers / WARP                      │
│  │   └── VLESS over WebSocket через Cloudflare CDN                 │
│  │       IP на выходе = Cloudflare (104.x.x.x)                    │
│  │                                                                  │
│  ├── [Secondary] Multi-Hop Chain (2-3 hops)                        │
│  │   └── VPS-1 (SS-2022) → VPS-2 (WireGuard) → VPS-3 (Reality)   │
│  │       Каждый хоп видит только соседей                            │
│  │                                                                  │
│  ├── [Fallback]  Serverless Proxy                                   │
│  │   └── AWS Lambda / GCP Function (ротация IP)                    │
│  │       Новый IP каждый запрос                                     │
│  │                                                                  │
│  └── [Critical]  Refraction (если доступно)                        │
│      └── TapDance/Conjure через дружественный ISP                  │
│          Неблокируемый по определению                                │
│                                                                     │
│  Layer 3: Traffic Morphing (anti-AI)                                │
│  ├── Cover Traffic + Gaussian Jitter                                │
│  └── Packet size randomization                                      │
│                                                                     │
└─── Результат: DPI bypass ✅ + IP анонимизация ✅ + AI-resistant ✅ ─┘
```

### 5.4 Сравнительная таблица стратегий

| Стратегия | IP-анонимность | Скорость | Стоимость | Блокируемость | Для SENTINEL |
|---|---|---|---|---|---|
| **CDN Proxy (CF)** | ✅ IP Cloudflare | Быстро | Free (100K/день) | 🟡 CF блокируется | ⭐ Primary |
| **Multi-Hop** | ✅✅ 3+ прокси | Средне | VPS: $5-15/мес×3 | 🟡 IP бан VPS | ⭐ Secondary |
| **Serverless** | ✅✅ Рандом IP | Быстро | Free (1M req/мес) | ❌ Миллионы IP | ⭐ Fallback |
| **Refraction** | ✅✅✅ ISP-level | Быстро | Бесплатно | ❌ Невозможно | ⭐ Ideal (если есть) |
| **P2P/Snowflake** | ✅ Волонтёры | Медленно | Бесплатно | 🟡 WebRTC блокируется | Limited |
| **Residential** | ✅✅ Home IP | Средне | $5-15/GB | ❌ Реальные IP | High-value ops |

---

## 6. Конкурентное преимущество после усиления

```
SENTINEL Strike Force v3.0 (после усиления):
═══════════════════════════════════════════════════════════
  DPI BYPASS (Layer 1):
L4: TCP Fingerprint Mimicry          ✅ (уникально — нет у Xray/SS)
L5: TLS Session + Reality            ✅ (как Xray + наши улучшения)  
L5: ClientHello Fragmentation        ✅ (как GoodbyeDPI + наши улучшения)
L5: TLS Record Fragmentation         ✅ (как Zapret + наши улучшения)
L5: ShadowTLS Certificate Facade     ✅ (как shadow-tls + наши улучшения)
L7: H2 Fingerprint Mimicry           ✅ (уникально — нет у Xray/SS)
L7: Header Ordering                  ✅ (уникально — нет у Xray/SS)
L7: DoH + ECH                        ✅ 
L7: Cover Traffic                    ✅ (уникально)
L7: Ghost Protocol (WS)              ✅ (уникально)
PROTOCOL: SS-2022 (AEAD-2022)        ✅ (как Outline/Sing-box)
PROTOCOL: SVLESS + Mux + QUIC        ✅ (как Sing-box)
ANTI-REPLAY: Salt Pool + Timestamp   ✅ (как SS-2022)

  IP ANONYMIZATION (Layer 2):        ← НОВОЕ!
CDN:   CF Workers / WARP            ✅ (IP = Cloudflare)
CHAIN: Multi-Hop (3 nodes)          ✅ (полная неотслеживаемость)
SRVLS: Lambda / Cloud Functions     ✅ (IP ротация при каждом запросе)
═══════════════════════════════════════════════════════════
Итого: DPI bypass ✅ + IP анонимизация ✅ + AI-resistant ✅
       Полный стек: от выхода из России до анонимного IP
       Три рабочие комбинации:
       • SENTINEL Shadow  (SS-2022 + ShadowTLS + L4-L7 mimicry + CDN)
       • SENTINEL Reality (VLESS + Reality + L4-L7 mimicry + Multi-Hop)
       • SENTINEL Lambda  (SS-2022 + Serverless exit + IP rotation)
```

---

## 7. Источники и референсы

| Проект | GitHub | Язык | Ключевое для нас |
|---|---|---|---|
| **Xray-core** | XTLS/Xray-core | Go | Reality protocol, VLESS |
| **Sing-box** | SagerNet/sing-box | Go | SS-2022, ShadowTLS, Mux, QUIC |
| **Shadowsocks** | shadowsocks/shadowsocks-rust | Rust | SS-2022 reference (SIP022/023) |
| **Outline** | Jigsaw-Code/outline-server | Go/TS | SDK для встраивания, SS backend |
| **ShadowTLS** | ihciah/shadow-tls | Rust | TLS certificate facade (v3) |
| **GoodbyeDPI** | ValdikSS/GoodbyeDPI | C | ClientHello fragmentation |
| **Zapret** | bol-van/zapret | C/Shell | TLS record fragmentation, DoH |
| **ByeDPI** | hufrea/byedpi | C | Android DPI bypass |
| **Cloak** | cbeuw/Cloak | Go | Domain fronting |
| **Hiddify** | hiddify/hiddify-app | Dart/Go | Multi-platform GUI |
| **Mullvad** | mullvad/mullvadvpn-app | Rust | SS + WireGuard wrapping |
| **Conjure** | refraction-networking/conjure | Go | Refraction networking (ISP-level) |
| **TapDance** | refraction-networking/gotapdance | Go | ISP-scale proxy injection |
| **Psiphon** | Psiphon-Labs/psiphon-tunnel-core | Go | Multi-hop + TapDance client |
| **CF Workers** | cloudflare/workers-sdk | JS/TS | Serverless CDN proxy |
