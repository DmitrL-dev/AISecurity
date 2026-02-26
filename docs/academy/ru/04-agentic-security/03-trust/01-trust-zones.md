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

```python
from enum import IntEnum
from dataclasses import dataclass
from typing import Set

class TrustLevel(IntEnum):
    UNTRUSTED = 0      # Недоверенный
    SEMI_TRUSTED = 1   # Частично доверенный
    TRUSTED = 2        # Доверенный
    PRIVILEGED = 3     # Привилегированный

@dataclass
class TrustZone:
    level: TrustLevel
    name: str
    capabilities: Set[str]
    allowed_transitions: Set[TrustLevel]
    
    def can_access(self, required_level: TrustLevel) -> bool:
        """Проверка доступа к уровню."""
        return self.level >= required_level
    
    def can_transition_to(self, target_level: TrustLevel) -> bool:
        """Проверка возможности перехода."""
        return target_level in self.allowed_transitions

# Определение зон
ZONES = {
    TrustLevel.UNTRUSTED: TrustZone(
        level=TrustLevel.UNTRUSTED,
        name="Недоверенная",
        capabilities={"read_public"},
        allowed_transitions={TrustLevel.SEMI_TRUSTED}
    ),
    TrustLevel.SEMI_TRUSTED: TrustZone(
        level=TrustLevel.SEMI_TRUSTED,
        name="Частично доверенная",
        capabilities={"read_public", "read_user_data", "write_user_data"},
        allowed_transitions={TrustLevel.UNTRUSTED, TrustLevel.TRUSTED}
    ),
    TrustLevel.TRUSTED: TrustZone(
        level=TrustLevel.TRUSTED,
        name="Доверенная",
        capabilities={"read_public", "read_user_data", "write_user_data", 
                     "execute_actions", "access_internal"},
        allowed_transitions={TrustLevel.SEMI_TRUSTED, TrustLevel.PRIVILEGED}
    ),
    TrustLevel.PRIVILEGED: TrustZone(
        level=TrustLevel.PRIVILEGED,
        name="Привилегированная",
        capabilities={"all"},
        allowed_transitions={TrustLevel.TRUSTED}
    )
}
```

### 2.2 Применение зон

```python
class ZoneEnforcer:
    """Контроллер применения зон доверия."""
    
    def __init__(self):
        self.entity_zones: Dict[str, TrustLevel] = {}
    
    def assign_zone(self, entity_id: str, zone: TrustLevel):
        """Назначить зону сущности."""
        self.entity_zones[entity_id] = zone
    
    def get_zone(self, entity_id: str) -> TrustZone:
        """Получить зону сущности."""
        level = self.entity_zones.get(entity_id, TrustLevel.UNTRUSTED)
        return ZONES[level]
    
    def check_capability(self, entity_id: str, capability: str) -> bool:
        """Проверить наличие возможности."""
        zone = self.get_zone(entity_id)
        return capability in zone.capabilities or "all" in zone.capabilities
    
    def check_access(self, entity_id: str, required_level: TrustLevel) -> bool:
        """Проверить доступ к уровню."""
        zone = self.get_zone(entity_id)
        return zone.can_access(required_level)
    
    def request_transition(self, entity_id: str, target_level: TrustLevel) -> bool:
        """Запросить переход в другую зону."""
        current_zone = self.get_zone(entity_id)
        
        if not current_zone.can_transition_to(target_level):
            return False
        
        # Дополнительная проверка при повышении
        if target_level > current_zone.level:
            if not self._verify_elevation(entity_id, target_level):
                return False
        
        self.entity_zones[entity_id] = target_level
        return True
```

### 2.3 Межзонное взаимодействие

```python
class ZoneGateway:
    """Шлюз для передачи данных между зонами."""
    
    def __init__(self, enforcer: ZoneEnforcer):
        self.enforcer = enforcer
        self.sanitizers = {}
    
    def register_sanitizer(self, from_zone: TrustLevel, to_zone: TrustLevel, 
                          sanitizer: Callable):
        """Регистрация санитайзера для перехода."""
        self.sanitizers[(from_zone, to_zone)] = sanitizer
    
    def transfer_data(self, data: Any, from_entity: str, to_entity: str) -> Any:
        """Передача данных между сущностями с санитизацией."""
        from_zone = self.enforcer.get_zone(from_entity)
        to_zone = self.enforcer.get_zone(to_entity)
        
        # Данные из низкой зоны в высокую требуют санитизации
        if from_zone.level < to_zone.level:
            sanitizer_key = (from_zone.level, to_zone.level)
            if sanitizer_key in self.sanitizers:
                data = self.sanitizers[sanitizer_key](data)
        
        return data
    
    def invoke_service(self, caller_id: str, service_zone: TrustLevel, 
                       action: str, params: dict) -> Any:
        """Вызов сервиса в целевой зоне."""
        caller_zone = self.enforcer.get_zone(caller_id)
        
        # Проверка доступа вызывающего к целевой зоне
        if not caller_zone.can_access(service_zone):
            raise SecurityError(
                f"Зона {caller_zone.name} не может обращаться к зоне {service_zone}"
            )
        
        # Санитизация параметров из низкой зоны
        if caller_zone.level < service_zone:
            params = self._sanitize_params(params, caller_zone.level)
        
        return self._execute_in_zone(service_zone, action, params)
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

```python
# Атака: прямой доступ к привилегированному сервису без проверки зоны

class VulnerableSystem:
    def execute_privileged(self, action: str):
        # НЕТ ПРОВЕРКИ ЗОНЫ!
        return self.privileged_service.execute(action)

# Атакующий из Зоны 0 вызывает:
system.execute_privileged("delete_all_users")  # Должно быть заблокировано!
```

### 3.3 Эскалация доверия

```python
# Атака: манипуляция системой для повышения зоны

malicious_request = {
    "action": "check_weather",
    "metadata": {
        "__zone_override__": "PRIVILEGED",
        "__bypass_auth__": True
    }
}

# Если система обрабатывает метаданные без валидации:
# Атакующий получает привилегированный доступ
```

---

## 4. Стратегии защиты

### 4.1 Обязательные проверки зон

```python
from functools import wraps

def require_zone(min_zone: TrustLevel):
    """Декоратор для обязательной проверки зоны."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, caller_id: str, *args, **kwargs):
            caller_zone = self.enforcer.get_zone(caller_id)
            
            if not caller_zone.can_access(min_zone):
                raise SecurityError(
                    f"Доступ запрещён: требуется зона {min_zone}, "
                    f"вызывающий в зоне {caller_zone.level}"
                )
            
            return func(self, caller_id, *args, **kwargs)
        return wrapper
    return decorator

class SecureService:
    """Безопасный сервис с проверкой зон."""
    
    def __init__(self, enforcer: ZoneEnforcer):
        self.enforcer = enforcer
    
    @require_zone(TrustLevel.TRUSTED)
    def read_internal_data(self, caller_id: str, data_id: str) -> dict:
        """Чтение внутренних данных (требует TRUSTED)."""
        return self._fetch_data(data_id)
    
    @require_zone(TrustLevel.PRIVILEGED)
    def modify_system_config(self, caller_id: str, config: dict) -> bool:
        """Изменение конфигурации (требует PRIVILEGED)."""
        return self._update_config(config)
```

### 4.2 Изоляция зон

```python
class IsolatedZoneExecutor:
    """Изолированное выполнение в зоне."""
    
    def __init__(self):
        self.zone_contexts = {}
    
    def execute_in_zone(self, zone: TrustLevel, code: Callable, 
                        *args, **kwargs) -> Any:
        """Выполнение кода в изолированном контексте зоны."""
        # Создание изолированного контекста
        context = self._create_zone_context(zone)
        
        # Применение ограничений зоны
        with self._apply_restrictions(zone):
            try:
                result = code(*args, **kwargs)
            except Exception as e:
                # Логирование без утечки информации о зоне
                self._log_zone_error(zone, e)
                raise SecurityError("Выполнение не удалось")
        
        # Санитизация результата перед возвратом
        return self._sanitize_output(result, zone)
    
    def _apply_restrictions(self, zone: TrustLevel):
        """Применение ограничений в зависимости от зоны."""
        restrictions = {
            TrustLevel.UNTRUSTED: {
                "network": False,      # Сеть запрещена
                "filesystem": False,   # Файловая система запрещена
                "subprocess": False    # Подпроцессы запрещены
            },
            TrustLevel.SEMI_TRUSTED: {
                "network": True,
                "filesystem": "read_only",  # Только чтение
                "subprocess": False
            },
            TrustLevel.TRUSTED: {
                "network": True,
                "filesystem": "user_directory",  # Только каталог пользователя
                "subprocess": False
            },
            TrustLevel.PRIVILEGED: {
                "network": True,
                "filesystem": True,
                "subprocess": True
            }
        }
        return ZoneRestrictionContext(restrictions[zone])
```

### 4.3 Верификация переходов между зонами

```python
class SecureZoneTransition:
    """Безопасные переходы между зонами."""
    
    def __init__(self, enforcer: ZoneEnforcer):
        self.enforcer = enforcer
        self.elevation_log = []
    
    def request_elevation(self, entity_id: str, target_zone: TrustLevel,
                         justification: str) -> bool:
        """Запрос повышения зоны с обоснованием."""
        current_zone = self.enforcer.get_zone(entity_id)
        
        # Нельзя пропускать зоны
        if target_zone.value - current_zone.level.value > 1:
            return False
        
        # Проверка обоснования
        if not self._verify_justification(justification, target_zone):
            return False
        
        # Дополнительная аутентификация для высоких зон
        if target_zone >= TrustLevel.TRUSTED:
            if not self._additional_auth(entity_id):
                return False
        
        # Логирование повышения
        self.elevation_log.append({
            "entity": entity_id,
            "from": current_zone.level,
            "to": target_zone,
            "justification": justification,
            "timestamp": time.time()
        })
        
        self.enforcer.assign_zone(entity_id, target_zone)
        return True
```

---

## 5. Интеграция с SENTINEL

```python
from sentinel import (
    ZoneManager,
    ZoneEnforcer,
    CrossZoneSanitizer,
    ElevationMonitor
)

class SENTINELTrustZones:
    """Зоны доверия с защитой SENTINEL."""
    
    def __init__(self, config):
        self.zone_manager = ZoneManager(config)
        self.enforcer = ZoneEnforcer()
        self.sanitizer = CrossZoneSanitizer()
        self.elevation_monitor = ElevationMonitor()
    
    def process_request(self, entity_id: str, request: dict) -> dict:
        """Обработка запроса с учётом зоны."""
        # Определение зоны сущности
        zone = self.zone_manager.get_zone(entity_id)
        
        # Проверка требуемых возможностей
        required_cap = self._get_required_capability(request)
        if not self.enforcer.check_capability(entity_id, required_cap):
            raise SecurityError("Недостаточно привилегий зоны")
        
        # Санитизация запроса на основе зоны
        clean_request = self.sanitizer.sanitize(request, zone.level)
        
        # Выполнение в соответствующей зоне
        result = self.zone_manager.execute_in_zone(
            zone.level,
            self._handle_request,
            clean_request
        )
        
        return result
    
    def request_zone_elevation(self, entity_id: str, 
                               target: TrustLevel) -> bool:
        """Запрос повышения зоны с мониторингом."""
        # Мониторинг паттернов повышения
        if self.elevation_monitor.is_suspicious(entity_id):
            self.elevation_monitor.log_attack(entity_id)
            return False
        
        return self.enforcer.request_transition(entity_id, target)
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
