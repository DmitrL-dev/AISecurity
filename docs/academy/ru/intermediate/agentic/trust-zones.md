# Зоны доверия

> **Уровень:** Средний  
> **Время:** 35 минут  
> **Трек:** 04 — Безопасность агентов  
> **Модуль:** 04.3 — Доверие и авторизация  
> **Версия:** 1.0

---

## Цели обучения

- [ ] Понимать концепцию зон доверия в AI-системах
- [ ] Проектировать границы доверия
- [ ] Реализовывать зональную безопасность

---

## 1. Что такое зоны доверия?

### 1.1 Определение

**Зона доверия** — логически изолированная область системы с определённым уровнем доверия.

```
┌────────────────────────────────────────────────────────────────────┐
│                    МОДЕЛЬ ЗОН ДОВЕРИЯ                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ ЗОНА 0: НЕДОВЕРЕННАЯ                                     │      │
│  │  • Внешние пользователи                                  │      │
│  │  • Непроверенные агенты                                  │      │
│  │  • Публичный интернет                                    │      │
│  │  ┌───────────────────────────────────────────────┐      │      │
│  │  │ ЗОНА 1: ЧАСТИЧНО ДОВЕРЕННАЯ                    │      │      │
│  │  │  • Аутентифицированные пользователи            │      │      │
│  │  │  • Проверенные внешние агенты                  │      │      │
│  │  │  ┌───────────────────────────────────────┐    │      │      │
│  │  │  │ ЗОНА 2: ДОВЕРЕННАЯ                     │    │      │      │
│  │  │  │  • Внутренние сервисы                  │    │      │      │
│  │  │  │  • Основные агенты                     │    │      │      │
│  │  │  │  ┌───────────────────────────────┐    │    │      │      │
│  │  │  │  │ ЗОНА 3: ПРИВИЛЕГИРОВАННАЯ      │    │    │      │      │
│  │  │  │  │  • Системные промпты           │    │    │      │      │
│  │  │  │  │  • Контроли безопасности       │    │    │      │      │
│  │  │  │  └───────────────────────────────┘    │    │      │      │
│  │  │  └───────────────────────────────────────┘    │      │      │
│  │  └───────────────────────────────────────────────┘      │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 1.2 Свойства зон

```
Свойства зон доверия:
├── Зона 0 (НЕДОВЕРЕННАЯ)
│   ├── Нет неявного доверия
│   ├── Весь ввод валидируется
│   └── Минимальные возможности
├── Зона 1 (ЧАСТИЧНО ДОВЕРЕННАЯ)
│   ├── Базовая аутентификация пройдена
│   ├── Ограниченные возможности
│   └── Действия логируются
├── Зона 2 (ДОВЕРЕННАЯ)
│   ├── Полная аутентификация
│   ├── Стандартные возможности
│   └── Межсервисное доверие
└── Зона 3 (ПРИВИЛЕГИРОВАННАЯ)
    ├── Максимальное доверие
    ├── Системный уровень доступа
    └── Контроли безопасности
```

---

## 2. Реализация

### 2.1 Определение зон

```rust
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
#[repr(u8)]
enum TrustLevel {
    Untrusted = 0,    // Недоверенный
    SemiTrusted = 1,  // Частично доверенный
    Trusted = 2,      // Доверенный
    Privileged = 3,   // Привилегированный
}

struct TrustZone {
    level: TrustLevel,
    name: String,
    capabilities: HashSet<String>,
    allowed_transitions: HashSet<TrustLevel>,
}

impl TrustZone {
    /// Проверка доступа к уровню.
    fn can_access(&self, required_level: TrustLevel) -> bool {
        self.level >= required_level
    }

    /// Проверка возможности перехода.
    fn can_transition_to(&self, target_level: TrustLevel) -> bool {
        self.allowed_transitions.contains(&target_level)
    }
}

// Определение зон
fn build_zones() -> HashMap<TrustLevel, TrustZone> {
    let mut zones = HashMap::new();
    zones.insert(TrustLevel::Untrusted, TrustZone {
        level: TrustLevel::Untrusted,
        name: "Недоверенная".to_string(),
        capabilities: HashSet::from(["read_public".into()]),
        allowed_transitions: HashSet::from([TrustLevel::SemiTrusted]),
    });
    zones.insert(TrustLevel::SemiTrusted, TrustZone {
        level: TrustLevel::SemiTrusted,
        name: "Частично доверенная".to_string(),
        capabilities: HashSet::from(["read_public".into(), "read_user_data".into(), "write_user_data".into()]),
        allowed_transitions: HashSet::from([TrustLevel::Untrusted, TrustLevel::Trusted]),
    });
    zones.insert(TrustLevel::Trusted, TrustZone {
        level: TrustLevel::Trusted,
        name: "Доверенная".to_string(),
        capabilities: HashSet::from([
            "read_public".into(), "read_user_data".into(), "write_user_data".into(),
            "execute_actions".into(), "access_internal".into(),
        ]),
        allowed_transitions: HashSet::from([TrustLevel::SemiTrusted, TrustLevel::Privileged]),
    });
    zones.insert(TrustLevel::Privileged, TrustZone {
        level: TrustLevel::Privileged,
        name: "Привилегированная".to_string(),
        capabilities: HashSet::from(["all".into()]),
        allowed_transitions: HashSet::from([TrustLevel::Trusted]),
    });
    zones
}
```

### 2.2 Применение зон

```rust
struct ZoneEnforcer {
    /// Контроллер применения зон доверия.
    entity_zones: HashMap<String, TrustLevel>,
}

impl ZoneEnforcer {
    fn new() -> Self {
        Self { entity_zones: HashMap::new() }
    }

    /// Назначить зону сущности.
    fn assign_zone(&mut self, entity_id: &str, zone: TrustLevel) {
        self.entity_zones.insert(entity_id.to_string(), zone);
    }

    /// Получить зону сущности.
    fn get_zone(&self, entity_id: &str) -> &TrustZone {
        let level = self.entity_zones.get(entity_id)
            .copied()
            .unwrap_or(TrustLevel::Untrusted);
        &ZONES[&level]
    }

    /// Проверить наличие возможности.
    fn check_capability(&self, entity_id: &str, capability: &str) -> bool {
        let zone = self.get_zone(entity_id);
        zone.capabilities.contains(capability) || zone.capabilities.contains("all")
    }

    /// Проверить доступ к уровню.
    fn check_access(&self, entity_id: &str, required_level: TrustLevel) -> bool {
        let zone = self.get_zone(entity_id);
        zone.can_access(required_level)
    }

    /// Запросить переход в другую зону.
    fn request_transition(&mut self, entity_id: &str, target_level: TrustLevel) -> bool {
        let current_zone = self.get_zone(entity_id);

        if !current_zone.can_transition_to(target_level) {
            return false;
        }

        // Дополнительная проверка при повышении
        if target_level > current_zone.level {
            if !self.verify_elevation(entity_id, target_level) {
                return false;
            }
        }

        self.entity_zones.insert(entity_id.to_string(), target_level);
        true
    }
}
```

### 2.3 Межзонное взаимодействие

```rust
struct ZoneGateway {
    /// Шлюз для передачи данных между зонами.
    enforcer: ZoneEnforcer,
    sanitizers: HashMap<(TrustLevel, TrustLevel), Box<dyn Fn(serde_json::Value) -> serde_json::Value>>,
}

impl ZoneGateway {
    fn new(enforcer: ZoneEnforcer) -> Self {
        Self {
            enforcer,
            sanitizers: HashMap::new(),
        }
    }

    /// Регистрация санитайзера для перехода.
    fn register_sanitizer(
        &mut self,
        from_zone: TrustLevel,
        to_zone: TrustLevel,
        sanitizer: Box<dyn Fn(serde_json::Value) -> serde_json::Value>,
    ) {
        self.sanitizers.insert((from_zone, to_zone), sanitizer);
    }

    /// Передача данных между сущностями с санитизацией.
    fn transfer_data(
        &self,
        mut data: serde_json::Value,
        from_entity: &str,
        to_entity: &str,
    ) -> serde_json::Value {
        let from_zone = self.enforcer.get_zone(from_entity);
        let to_zone = self.enforcer.get_zone(to_entity);

        // Данные из низкой зоны в высокую требуют санитизации
        if from_zone.level < to_zone.level {
            let sanitizer_key = (from_zone.level, to_zone.level);
            if let Some(sanitizer) = self.sanitizers.get(&sanitizer_key) {
                data = sanitizer(data);
            }
        }

        data
    }

    /// Вызов сервиса в целевой зоне.
    fn invoke_service(
        &self,
        caller_id: &str,
        service_zone: TrustLevel,
        action: &str,
        mut params: HashMap<String, serde_json::Value>,
    ) -> Result<serde_json::Value, String> {
        let caller_zone = self.enforcer.get_zone(caller_id);

        // Проверка доступа вызывающего к целевой зоне
        if !caller_zone.can_access(service_zone) {
            return Err(format!(
                "Зона {} не может обращаться к зоне {:?}",
                caller_zone.name, service_zone
            ));
        }

        // Санитизация параметров из низкой зоны
        if caller_zone.level < service_zone {
            params = self.sanitize_params(params, caller_zone.level);
        }

        self.execute_in_zone(service_zone, action, params)
    }
}
```

---

## 3. Угрозы безопасности

### 3.1 Модель угроз

```
Угрозы зон доверия:
├── Обход зоны
│   └── Пропуск проверок для доступа к высшей зоне
├── Путаница зон
│   └── Обман системы относительно зоны сущности
├── Эскалация доверия
│   └── Нелегитимное повышение до высшей зоны
├── Межзонная инъекция
│   └── Внедрение вредоносных данных через зоны
└── Коллапс зоны
    └── Компрометация границы зоны
```

### 3.2 Атака обхода зоны

```rust
// Атака: прямой доступ к привилегированному сервису без проверки зоны

struct VulnerableSystem {
    privileged_service: PrivilegedService,
}

impl VulnerableSystem {
    fn execute_privileged(&self, action: &str) -> Result<(), String> {
        // НЕТ ПРОВЕРКИ ЗОНЫ!
        self.privileged_service.execute(action)
    }
}

// Атакующий из Зоны 0 вызывает:
system.execute_privileged("delete_all_users"); // Должно быть заблокировано!
```

### 3.3 Эскалация доверия

```rust
// Атака: манипуляция системой для повышения зоны

let malicious_request = serde_json::json!({
    "action": "check_weather",
    "metadata": {
        "__zone_override__": "PRIVILEGED",
        "__bypass_auth__": true
    }
});

// Если система обрабатывает метаданные без валидации:
// Атакующий получает привилегированный доступ
```

---

## 4. Стратегии защиты

### 4.1 Обязательные проверки зон

```rust
/// Обязательная проверка зоны перед выполнением метода.
fn require_zone(
    enforcer: &ZoneEnforcer,
    caller_id: &str,
    min_zone: TrustLevel,
) -> Result<(), String> {
    let caller_zone = enforcer.get_zone(caller_id);

    if !caller_zone.can_access(min_zone) {
        return Err(format!(
            "Доступ запрещён: требуется зона {:?}, вызывающий в зоне {:?}",
            min_zone, caller_zone.level
        ));
    }

    Ok(())
}

struct SecureService {
    /// Безопасный сервис с проверкой зон.
    enforcer: ZoneEnforcer,
}

impl SecureService {
    fn new(enforcer: ZoneEnforcer) -> Self {
        Self { enforcer }
    }

    /// Чтение внутренних данных (требует TRUSTED).
    fn read_internal_data(&self, caller_id: &str, data_id: &str) -> Result<serde_json::Value, String> {
        require_zone(&self.enforcer, caller_id, TrustLevel::Trusted)?;
        self.fetch_data(data_id)
    }

    /// Изменение конфигурации (требует PRIVILEGED).
    fn modify_system_config(&self, caller_id: &str, config: &serde_json::Value) -> Result<bool, String> {
        require_zone(&self.enforcer, caller_id, TrustLevel::Privileged)?;
        self.update_config(config)
    }
}
```

### 4.2 Изоляция зон

```rust
use std::collections::HashMap;

struct IsolatedZoneExecutor {
    /// Изолированное выполнение в зоне.
    zone_contexts: HashMap<TrustLevel, ZoneContext>,
}

impl IsolatedZoneExecutor {
    fn new() -> Self {
        Self { zone_contexts: HashMap::new() }
    }

    /// Выполнение кода в изолированном контексте зоны.
    fn execute_in_zone<F, R>(&self, zone: TrustLevel, code: F) -> Result<R, String>
    where
        F: FnOnce() -> R,
    {
        // Создание изолированного контекста
        let _context = self.create_zone_context(zone);

        // Применение ограничений зоны
        let _guard = self.apply_restrictions(zone);
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| code()));

        match result {
            Ok(value) => {
                // Санитизация результата перед возвратом
                Ok(value)
            }
            Err(_) => {
                // Логирование без утечки информации о зоне
                self.log_zone_error(zone, "Паника в зоне выполнения");
                Err("Выполнение не удалось".to_string())
            }
        }
    }

    /// Применение ограничений в зависимости от зоны.
    fn apply_restrictions(&self, zone: TrustLevel) -> ZoneRestrictionGuard {
        let restrictions = match zone {
            TrustLevel::Untrusted => ZoneRestrictions {
                network: false,           // Сеть запрещена
                filesystem: FilePerm::None,  // Файловая система запрещена
                subprocess: false,        // Подпроцессы запрещены
            },
            TrustLevel::SemiTrusted => ZoneRestrictions {
                network: true,
                filesystem: FilePerm::ReadOnly,  // Только чтение
                subprocess: false,
            },
            TrustLevel::Trusted => ZoneRestrictions {
                network: true,
                filesystem: FilePerm::UserDirectory,  // Только каталог пользователя
                subprocess: false,
            },
            TrustLevel::Privileged => ZoneRestrictions {
                network: true,
                filesystem: FilePerm::Full,
                subprocess: true,
            },
        };
        ZoneRestrictionGuard::new(restrictions)
    }
}
```

### 4.3 Верификация переходов между зонами

```rust
struct ElevationRecord {
    entity: String,
    from: TrustLevel,
    to: TrustLevel,
    justification: String,
    timestamp: f64,
}

struct SecureZoneTransition {
    /// Безопасные переходы между зонами.
    enforcer: ZoneEnforcer,
    elevation_log: Vec<ElevationRecord>,
}

impl SecureZoneTransition {
    fn new(enforcer: ZoneEnforcer) -> Self {
        Self {
            enforcer,
            elevation_log: Vec::new(),
        }
    }

    /// Запрос повышения зоны с обоснованием.
    fn request_elevation(
        &mut self,
        entity_id: &str,
        target_zone: TrustLevel,
        justification: &str,
    ) -> bool {
        let current_zone = self.enforcer.get_zone(entity_id);

        // Нельзя пропускать зоны
        if (target_zone as i32) - (current_zone.level as i32) > 1 {
            return false;
        }

        // Проверка обоснования
        if !self.verify_justification(justification, target_zone) {
            return false;
        }

        // Дополнительная аутентификация для высоких зон
        if target_zone >= TrustLevel::Trusted {
            if !self.additional_auth(entity_id) {
                return false;
            }
        }

        // Логирование повышения
        self.elevation_log.push(ElevationRecord {
            entity: entity_id.to_string(),
            from: current_zone.level,
            to: target_zone,
            justification: justification.to_string(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
        });

        self.enforcer.assign_zone(entity_id, target_zone);
        true
    }
}
```

---

## 5. Интеграция с SENTINEL

```rust
use sentinel_core::engines::SentinelEngine;

let engine = SentinelEngine::new();

// Сканирование межзонных запросов на попытки эскалации
let request_text = format!("[zone:{}][entity:{}] {}", zone_level, entity_id, request_action);
let result = engine.analyze(&request_text);

if result.detected {
    log::warn!(
        "Угроза зоны доверия: entity={}, zone={}, risk={}, categories={:?}, time={}μs",
        entity_id, zone_level, result.risk_score, result.categories, result.processing_time_us
    );
    // Блокировка межзонного запроса
}

// Сканирование обоснований повышения зоны на манипуляции
let elevation_check = engine.analyze(&elevation_justification);
if elevation_check.detected {
    log::warn!("Атака эскалации зоны заблокирована: risk={}", elevation_check.risk_score);
}
```

---

## 6. Итоги

1. **Зоны доверия:** Многоуровневая модель доверия (0-3)
2. **Свойства:** Возможности, переходы, изоляция
3. **Угрозы:** Обход, эскалация, инъекция
4. **Защита:** Обязательные проверки, изоляция, верификация

---

## Следующий урок

→ [02. Безопасность на основе возможностей](02-capability-based-security.md)

---

*AI Security Academy | Трек 04: Безопасность агентов | Модуль 04.3: Доверие и авторизация*
