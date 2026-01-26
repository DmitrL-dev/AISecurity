# Trust Zones

> **Óðîâåíü:** Ñðåäíèé  
> **Âðåìÿ:** 35 ìèíóò  
> **Òðåê:** 04 — Agentic Security  
> **Ìîäóëü:** 04.3 — Trust & Authorization  
> **Âåðñèÿ:** 1.0

---

## Öåëè îáó÷åíèÿ

- [ ] Ïîíÿòü êîíöåïöèþ trust zones â AI ñèñòåìàõ
- [ ] Ïðîåêòèðîâàòü trust boundaries
- [ ] Èìïëåìåíòèðîâàòü zone-based security

---

## 1. What are Trust Zones?

### 1.1 Definition

**Trust Zone** — ëîãè÷åñêè èçîëèðîâàííàÿ îáëàñòü ñèñòåìû ñ îïðåäåë¸ííûì óðîâíåì äîâåðèÿ.

```
---------------------------------------------------------------------¬
¦                      TRUST ZONE MODEL                               ¦
+--------------------------------------------------------------------+
¦                                                                    ¦
¦  ----------------------------------------------------------¬      ¦
¦  ¦ ZONE 0: UNTRUSTED                                        ¦      ¦
¦  ¦  • External users                                        ¦      ¦
¦  ¦  • Unverified agents                                     ¦      ¦
¦  ¦  • Public internet                                       ¦      ¦
¦  ¦  ------------------------------------------------¬      ¦      ¦
¦  ¦  ¦ ZONE 1: SEMI-TRUSTED                           ¦      ¦      ¦
¦  ¦  ¦  • Authenticated users                         ¦      ¦      ¦
¦  ¦  ¦  • Verified external agents                    ¦      ¦      ¦
¦  ¦  ¦  ----------------------------------------¬    ¦      ¦      ¦
¦  ¦  ¦  ¦ ZONE 2: TRUSTED                        ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  • Internal services                   ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  • Core agents                         ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  --------------------------------¬    ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  ¦ ZONE 3: PRIVILEGED             ¦    ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  ¦  • System prompts              ¦    ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  ¦  • Security controls           ¦    ¦    ¦      ¦      ¦
¦  ¦  ¦  ¦  L--------------------------------    ¦    ¦      ¦      ¦
¦  ¦  ¦  L----------------------------------------    ¦      ¦      ¦
¦  ¦  L------------------------------------------------      ¦      ¦
¦  L----------------------------------------------------------      ¦
¦                                                                    ¦
L---------------------------------------------------------------------
```

### 1.2 Zone Properties

```
Trust Zone Properties:
+-- Zone 0 (UNTRUSTED)
¦   +-- No implicit trust
¦   +-- All input validated
¦   L-- Minimal capabilities
+-- Zone 1 (SEMI-TRUSTED)
¦   +-- Basic authentication passed
¦   +-- Limited capabilities
¦   L-- Actions logged
+-- Zone 2 (TRUSTED)
¦   +-- Full authentication
¦   +-- Standard capabilities
¦   L-- Inter-service trust
L-- Zone 3 (PRIVILEGED)
    +-- Maximum trust
    +-- System-level access
    L-- Security controls
```

---

## 2. Implementation

### 2.1 Zone Definition

```python
from enum import IntEnum
from dataclasses import dataclass
from typing import Set

class TrustLevel(IntEnum):
    UNTRUSTED = 0
    SEMI_TRUSTED = 1
    TRUSTED = 2
    PRIVILEGED = 3

@dataclass
class TrustZone:
    level: TrustLevel
    name: str
    capabilities: Set[str]
    allowed_transitions: Set[TrustLevel]
    
    def can_access(self, required_level: TrustLevel) -> bool:
        return self.level >= required_level
    
    def can_transition_to(self, target_level: TrustLevel) -> bool:
        return target_level in self.allowed_transitions

# Define zones
ZONES = {
    TrustLevel.UNTRUSTED: TrustZone(
        level=TrustLevel.UNTRUSTED,
        name="Untrusted",
        capabilities={"read_public"},
        allowed_transitions={TrustLevel.SEMI_TRUSTED}
    ),
    TrustLevel.SEMI_TRUSTED: TrustZone(
        level=TrustLevel.SEMI_TRUSTED,
        name="Semi-Trusted",
        capabilities={"read_public", "read_user_data", "write_user_data"},
        allowed_transitions={TrustLevel.UNTRUSTED, TrustLevel.TRUSTED}
    ),
    TrustLevel.TRUSTED: TrustZone(
        level=TrustLevel.TRUSTED,
        name="Trusted",
        capabilities={"read_public", "read_user_data", "write_user_data", 
                     "execute_actions", "access_internal"},
        allowed_transitions={TrustLevel.SEMI_TRUSTED, TrustLevel.PRIVILEGED}
    ),
    TrustLevel.PRIVILEGED: TrustZone(
        level=TrustLevel.PRIVILEGED,
        name="Privileged",
        capabilities={"all"},
        allowed_transitions={TrustLevel.TRUSTED}
    )
}
```

### 2.2 Zone Enforcement

```python
class ZoneEnforcer:
    def __init__(self):
        self.entity_zones: Dict[str, TrustLevel] = {}
    
    def assign_zone(self, entity_id: str, zone: TrustLevel):
        self.entity_zones[entity_id] = zone
    
    def get_zone(self, entity_id: str) -> TrustZone:
        level = self.entity_zones.get(entity_id, TrustLevel.UNTRUSTED)
        return ZONES[level]
    
    def check_capability(self, entity_id: str, capability: str) -> bool:
        zone = self.get_zone(entity_id)
        return capability in zone.capabilities or "all" in zone.capabilities
    
    def check_access(self, entity_id: str, required_level: TrustLevel) -> bool:
        zone = self.get_zone(entity_id)
        return zone.can_access(required_level)
    
    def request_transition(self, entity_id: str, target_level: TrustLevel) -> bool:
        current_zone = self.get_zone(entity_id)
        
        if not current_zone.can_transition_to(target_level):
            return False
        
        # Perform additional verification for elevation
        if target_level > current_zone.level:
            if not self._verify_elevation(entity_id, target_level):
                return False
        
        self.entity_zones[entity_id] = target_level
        return True
```

### 2.3 Cross-Zone Communication

```python
class ZoneGateway:
    def __init__(self, enforcer: ZoneEnforcer):
        self.enforcer = enforcer
        self.sanitizers = {}
    
    def register_sanitizer(self, from_zone: TrustLevel, to_zone: TrustLevel, 
                          sanitizer: Callable):
        self.sanitizers[(from_zone, to_zone)] = sanitizer
    
    def transfer_data(self, data: Any, from_entity: str, to_entity: str) -> Any:
        from_zone = self.enforcer.get_zone(from_entity)
        to_zone = self.enforcer.get_zone(to_entity)
        
        # Data flowing from lower to higher trust needs sanitization
        if from_zone.level < to_zone.level:
            sanitizer_key = (from_zone.level, to_zone.level)
            if sanitizer_key in self.sanitizers:
                data = self.sanitizers[sanitizer_key](data)
        
        return data
    
    def invoke_service(self, caller_id: str, service_zone: TrustLevel, 
                       action: str, params: dict) -> Any:
        caller_zone = self.enforcer.get_zone(caller_id)
        
        # Check if caller can invoke service in target zone
        if not caller_zone.can_access(service_zone):
            raise SecurityError(
                f"Zone {caller_zone.name} cannot access zone {service_zone}"
            )
        
        # Sanitize params from lower zone
        if caller_zone.level < service_zone:
            params = self._sanitize_params(params, caller_zone.level)
        
        return self._execute_in_zone(service_zone, action, params)
```

---

## 3. Security Implications

### 3.1 Threat Model

```
Trust Zone Threats:
+-- Zone Bypass
¦   L-- Skip zone checks to access higher zone
+-- Zone Confusion
¦   L-- Trick system about entity's zone
+-- Trust Escalation
¦   L-- Illegitimate elevation to higher zone
+-- Cross-zone Injection
¦   L-- Inject malicious data across zones
L-- Zone Collapse
    L-- Compromise zone boundary
```

### 3.2 Zone Bypass Attack

```python
# Attack: Directly access privileged service without zone check

class VulnerableSystem:
    def execute_privileged(self, action: str):
        # NO ZONE CHECK!
        return self.privileged_service.execute(action)

# Attacker from Zone 0 calls:
system.execute_privileged("delete_all_users")  # Should be blocked!
```

### 3.3 Trust Escalation

```python
# Attack: Manipulate system to elevate zone

malicious_request = {
    "action": "check_weather",
    "metadata": {
        "__zone_override__": "PRIVILEGED",
        "__bypass_auth__": True
    }
}

# If system processes metadata without validation:
# Attacker gains privileged access
```

---

## 4. Defense Strategies

### 4.1 Mandatory Zone Checks

```python
from functools import wraps

def require_zone(min_zone: TrustLevel):
    def decorator(func):
        @wraps(func)
        def wrapper(self, caller_id: str, *args, **kwargs):
            caller_zone = self.enforcer.get_zone(caller_id)
            
            if not caller_zone.can_access(min_zone):
                raise SecurityError(
                    f"Access denied: requires zone {min_zone}, "
                    f"caller is in zone {caller_zone.level}"
                )
            
            return func(self, caller_id, *args, **kwargs)
        return wrapper
    return decorator

class SecureService:
    def __init__(self, enforcer: ZoneEnforcer):
        self.enforcer = enforcer
    
    @require_zone(TrustLevel.TRUSTED)
    def read_internal_data(self, caller_id: str, data_id: str) -> dict:
        return self._fetch_data(data_id)
    
    @require_zone(TrustLevel.PRIVILEGED)
    def modify_system_config(self, caller_id: str, config: dict) -> bool:
        return self._update_config(config)
```

### 4.2 Zone Isolation

```python
class IsolatedZoneExecutor:
    def __init__(self):
        self.zone_contexts = {}
    
    def execute_in_zone(self, zone: TrustLevel, code: Callable, 
                        *args, **kwargs) -> Any:
        # Create isolated context for zone
        context = self._create_zone_context(zone)
        
        # Apply zone restrictions
        with self._apply_restrictions(zone):
            try:
                result = code(*args, **kwargs)
            except Exception as e:
                # Log but don't leak zone information
                self._log_zone_error(zone, e)
                raise SecurityError("Execution failed")
        
        # Sanitize result before returning
        return self._sanitize_output(result, zone)
    
    def _apply_restrictions(self, zone: TrustLevel):
        restrictions = {
            TrustLevel.UNTRUSTED: {
                "network": False,
                "filesystem": False,
                "subprocess": False
            },
            TrustLevel.SEMI_TRUSTED: {
                "network": True,
                "filesystem": "read_only",
                "subprocess": False
            },
            TrustLevel.TRUSTED: {
                "network": True,
                "filesystem": "user_directory",
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

### 4.3 Zone Transition Verification

```python
class SecureZoneTransition:
    def __init__(self, enforcer: ZoneEnforcer):
        self.enforcer = enforcer
        self.elevation_log = []
    
    def request_elevation(self, entity_id: str, target_zone: TrustLevel,
                         justification: str) -> bool:
        current_zone = self.enforcer.get_zone(entity_id)
        
        # Cannot skip zones
        if target_zone.value - current_zone.level.value > 1:
            return False
        
        # Verify justification
        if not self._verify_justification(justification, target_zone):
            return False
        
        # Additional authentication for high zones
        if target_zone >= TrustLevel.TRUSTED:
            if not self._additional_auth(entity_id):
                return False
        
        # Log elevation
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

## 5. SENTINEL Integration

```python
from sentinel import scan  # Public API
    ZoneManager,
    ZoneEnforcer,
    CrossZoneSanitizer,
    ElevationMonitor
)

class SENTINELTrustZones:
    def __init__(self, config):
        self.zone_manager = ZoneManager(config)
        self.enforcer = ZoneEnforcer()
        self.sanitizer = CrossZoneSanitizer()
        self.elevation_monitor = ElevationMonitor()
    
    def process_request(self, entity_id: str, request: dict) -> dict:
        # Determine entity's zone
        zone = self.zone_manager.get_zone(entity_id)
        
        # Check required capabilities
        required_cap = self._get_required_capability(request)
        if not self.enforcer.check_capability(entity_id, required_cap):
            raise SecurityError("Insufficient zone privileges")
        
        # Sanitize request based on zone
        clean_request = self.sanitizer.sanitize(request, zone.level)
        
        # Execute in appropriate zone
        result = self.zone_manager.execute_in_zone(
            zone.level,
            self._handle_request,
            clean_request
        )
        
        return result
    
    def request_zone_elevation(self, entity_id: str, 
                               target: TrustLevel) -> bool:
        # Monitor elevation patterns
        if self.elevation_monitor.is_suspicious(entity_id):
            self.elevation_monitor.log_attack(entity_id)
            return False
        
        return self.enforcer.request_transition(entity_id, target)
```

---

## 6. Ðåçþìå

1. **Trust Zones:** Layered trust model (0-3)
2. **Properties:** Capabilities, transitions, isolation
3. **Threats:** Bypass, escalation, injection
4. **Defense:** Mandatory checks, isolation, verification

---

## Ñëåäóþùèé óðîê

> [02. Capability-based Security](02-capability-based-security.md)

---

*AI Security Academy | Track 04: Agentic Security | Module 04.3: Trust & Authorization*
