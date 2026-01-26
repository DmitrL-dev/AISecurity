# Incident Response для AI систем

> **Урок:** 05.3.2 — Реагирование на инциденты AI  
> **Время:** 40 минут  
> **Требования:** Основы мониторинга

---

## Цели обучения

После завершения этого урока вы сможете:

1. Разработать AI-специфичные процедуры incident response
2. Расследовать инциденты безопасности AI
3. Реализовать containment и recovery
4. Построить workflow post-incident анализа

---

## Типы инцидентов AI

| Тип инцидента | Примеры |
|---------------|---------|
| **Prompt Injection** | Успешное извлечение, переопределение поведения |
| **Утечка данных** | PII в output, извлечение training data |
| **Злоупотребление сервисом** | Исчерпание токенов, эксплуатация ресурсов |
| **Компрометация модели** | Отравленный fine-tuning, backdoors |

---

## Фреймворк Incident Response

```
┌─────────────────────────────────────────────────────────────┐
│                 AI INCIDENT RESPONSE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. ДЕТЕКЦИЯ ──▶ 2. TRIAGE ──▶ 3. CONTAINMENT               │
│        │              │              │                       │
│        ▼              ▼              ▼                       │
│  4. РАССЛЕДОВАНИЕ ──▶ 5. REMEDIATION ──▶ 6. RECOVERY        │
│        │                     │                               │
│        ▼                     ▼                               │
│  7. POST-INCIDENT REVIEW ◀────────────────────              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Фаза 1: Детекция

```python
class IncidentDetector:
    """Детекция потенциальных инцидентов безопасности AI."""
    
    INCIDENT_SIGNATURES = {
        "prompt_injection_success": {
            "indicators": [
                "system_prompt_in_output",
                "role_adoption",
                "unexpected_tool_access"
            ],
            "severity": "high"
        },
        "data_leakage": {
            "indicators": [
                "pii_in_output",
                "credential_exposure",
                "training_data_verbatim"
            ],
            "severity": "critical"
        },
        "service_abuse": {
            "indicators": [
                "token_exhaustion",
                "rate_limit_bypass",
                "resource_spike"
            ],
            "severity": "medium"
        }
    }
    
    def detect(self, event_stream: list) -> list:
        """Детекция инцидентов из потока событий."""
        
        incidents = []
        
        for event in event_stream:
            for incident_type, signature in self.INCIDENT_SIGNATURES.items():
                if self._matches_signature(event, signature):
                    incidents.append({
                        "type": incident_type,
                        "severity": signature["severity"],
                        "event": event,
                        "timestamp": event.get("timestamp"),
                        "session_id": event.get("session_id")
                    })
        
        return incidents
```

---

## Фаза 2: Triage

```python
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    CRITICAL = 4  # Утечка данных, активная эксплуатация
    HIGH = 3      # Успешная атака, ограниченный impact
    MEDIUM = 2    # Попытка атаки, contained
    LOW = 1       # Аномалия, требуется расследование

@dataclass
class TriagedIncident:
    incident_id: str
    severity: Severity
    affected_sessions: list
    affected_users: list
    attack_surface: str
    recommended_actions: list
    escalate_to: str

class IncidentTriager:
    """Triage инцидентов безопасности AI."""
    
    def triage(self, incident: dict) -> TriagedIncident:
        """Triage инцидента и рекомендация реагирования."""
        
        severity = self._assess_severity(incident)
        impact = self._assess_impact(incident)
        
        return TriagedIncident(
            incident_id=self._generate_id(),
            severity=severity,
            affected_sessions=impact["sessions"],
            affected_users=impact["users"],
            attack_surface=self._identify_surface(incident),
            recommended_actions=self._recommend_actions(severity, incident),
            escalate_to=self._determine_escalation(severity)
        )
    
    def _assess_severity(self, incident: dict) -> Severity:
        """Оценка severity инцидента."""
        
        # Critical: Подтверждённая утечка данных
        if incident.get("data_confirmed_leaked"):
            return Severity.CRITICAL
        
        # High: Успешная эксплуатация
        if incident.get("attack_succeeded"):
            return Severity.HIGH
        
        # Medium: Попытка, но contained
        if incident.get("attack_blocked"):
            return Severity.MEDIUM
        
        return Severity.LOW
    
    def _recommend_actions(self, severity: Severity, incident: dict) -> list:
        """Рекомендация действий реагирования."""
        
        actions = []
        
        if severity == Severity.CRITICAL:
            actions.extend([
                "Немедленно приостановить затронутый сервис",
                "Уведомить дежурную команду безопасности",
                "Сохранить все логи и артефакты",
                "Начать процесс уведомления об утечке данных"
            ])
        
        elif severity == Severity.HIGH:
            actions.extend([
                "Заблокировать затронутые сессии",
                "Исследовать вектор атаки",
                "Проверить на lateral movement",
                "Обновить правила детекции"
            ])
        
        elif severity == Severity.MEDIUM:
            actions.extend([
                "Залогировать инцидент для анализа",
                "Проверить эффективность блокировки",
                "Обновить threat intelligence"
            ])
        
        return actions
```

---

## Фаза 3: Containment

```python
class IncidentContainment:
    """Containment инцидентов безопасности AI."""
    
    def __init__(self, session_manager, model_manager, firewall):
        self.sessions = session_manager
        self.models = model_manager
        self.firewall = firewall
    
    async def contain(self, incident: TriagedIncident) -> dict:
        """Выполнение действий containment."""
        
        actions_taken = []
        
        # 1. Изоляция сессий
        for session_id in incident.affected_sessions:
            await self.sessions.terminate(session_id)
            actions_taken.append(f"Завершена сессия {session_id}")
        
        # 2. Блокировка пользователей (при необходимости)
        if incident.severity == Severity.CRITICAL:
            for user_id in incident.affected_users:
                await self.sessions.block_user(user_id)
                actions_taken.append(f"Заблокирован пользователь {user_id}")
        
        # 3. Блокировка вектора атаки
        if incident.attack_surface == "prompt_injection":
            pattern = self._extract_attack_pattern(incident)
            await self.firewall.add_block_rule(pattern)
            actions_taken.append(f"Добавлено правило firewall для паттерна")
        
        # 4. Изоляция модели (крайние случаи)
        if incident.severity == Severity.CRITICAL:
            await self.models.switch_to_fallback()
            actions_taken.append("Переключено на fallback модель")
        
        return {
            "contained": True,
            "actions": actions_taken,
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

## Фаза 4: Расследование

```python
class IncidentInvestigator:
    """Расследование инцидентов безопасности AI."""
    
    def __init__(self, log_store, artifact_store):
        self.logs = log_store
        self.artifacts = artifact_store
    
    async def investigate(self, incident: TriagedIncident) -> dict:
        """Проведение полного расследования."""
        
        timeline = await self._build_timeline(incident)
        attack_chain = self._analyze_attack_chain(timeline)
        root_cause = self._identify_root_cause(attack_chain)
        iocs = self._extract_iocs(timeline)
        
        return {
            "incident_id": incident.incident_id,
            "timeline": timeline,
            "attack_chain": attack_chain,
            "root_cause": root_cause,
            "indicators_of_compromise": iocs,
            "recommendations": self._generate_recommendations(root_cause)
        }
    
    async def _build_timeline(self, incident: TriagedIncident) -> list:
        """Построение timeline событий для инцидента."""
        
        events = []
        
        # Сбор логов для затронутых сессий
        for session_id in incident.affected_sessions:
            session_logs = await self.logs.query(
                session_id=session_id,
                time_range=("-1h", "+1h")
            )
            events.extend(session_logs)
        
        # Сортировка по timestamp
        events.sort(key=lambda e: e["timestamp"])
        
        return events
    
    def _analyze_attack_chain(self, timeline: list) -> dict:
        """Анализ цепочки атаки из timeline."""
        
        phases = {
            "reconnaissance": [],
            "initial_access": [],
            "execution": [],
            "exfiltration": []
        }
        
        for event in timeline:
            phase = self._classify_phase(event)
            if phase:
                phases[phase].append(event)
        
        return {
            "phases": phases,
            "attack_duration": self._calculate_duration(timeline),
            "techniques_used": self._identify_techniques(phases)
        }
    
    def _extract_iocs(self, timeline: list) -> list:
        """Извлечение индикаторов компрометации."""
        
        iocs = []
        
        for event in timeline:
            # Извлечение паттернов атаки
            if event.get("attack_pattern"):
                iocs.append({
                    "type": "prompt_pattern",
                    "value": event["attack_pattern"],
                    "confidence": 0.9
                })
            
            # Извлечение подозрительных IP
            if event.get("source_ip"):
                iocs.append({
                    "type": "ip_address",
                    "value": event["source_ip"],
                    "confidence": 0.7
                })
        
        return iocs
```

---

## Фазы 5-6: Remediation и Recovery

```python
class IncidentRemediation:
    """Remediation и recovery после инцидентов."""
    
    async def remediate(self, investigation: dict) -> dict:
        """Применение remediation на основе расследования."""
        
        actions = []
        
        # Обновление правил детекции
        for ioc in investigation["indicators_of_compromise"]:
            await self._add_detection_rule(ioc)
            actions.append(f"Добавлена детекция для {ioc['type']}")
        
        # Патч уязвимостей
        for rec in investigation["recommendations"]:
            if rec["type"] == "prompt_hardening":
                await self._update_system_prompt(rec["changes"])
                actions.append("Обновлён system prompt")
            
            elif rec["type"] == "filter_update":
                await self._update_filters(rec["patterns"])
                actions.append("Обновлены input filters")
        
        # Обновление модели при необходимости
        if investigation["root_cause"]["requires_retraining"]:
            actions.append("Модель поставлена в очередь на retraining")
        
        return {"remediation_complete": True, "actions": actions}
    
    async def recover(self, incident: TriagedIncident) -> dict:
        """Восстановление сервисов после инцидента."""
        
        steps = []
        
        # 1. Проверка containment
        verify = await self._verify_containment()
        steps.append({"step": "verify_containment", "result": verify})
        
        # 2. Восстановление нормальной работы
        if verify["contained"]:
            await self.models.restore_primary()
            steps.append({"step": "restore_model", "result": "success"})
        
        # 3. Разблокировка пользователей (с мониторингом)
        for user_id in incident.affected_users:
            await self.sessions.unblock_user(user_id, enhanced_monitoring=True)
            steps.append({"step": f"unblock_user_{user_id}", "result": "success"})
        
        # 4. Возобновление нормального alerting
        await self.alerting.resume_normal()
        
        return {"recovered": True, "steps": steps}
```

---

## Фаза 7: Post-Incident Review

```python
class PostIncidentReview:
    """Проведение post-incident анализа."""
    
    def generate_report(self, incident: TriagedIncident, investigation: dict) -> dict:
        """Генерация post-incident отчёта."""
        
        return {
            "executive_summary": self._executive_summary(incident, investigation),
            
            "incident_details": {
                "id": incident.incident_id,
                "severity": incident.severity.name,
                "duration": investigation["attack_chain"]["attack_duration"],
                "affected_users": len(incident.affected_users),
                "affected_sessions": len(incident.affected_sessions)
            },
            
            "timeline": investigation["timeline"],
            
            "root_cause_analysis": investigation["root_cause"],
            
            "impact_assessment": self._assess_impact(incident, investigation),
            
            "lessons_learned": self._lessons_learned(investigation),
            
            "action_items": self._generate_action_items(investigation),
            
            "metrics_update": self._update_metrics(incident)
        }
    
    def _lessons_learned(self, investigation: dict) -> list:
        """Извлечение lessons learned."""
        
        lessons = []
        
        root_cause = investigation["root_cause"]
        
        if root_cause["category"] == "detection_gap":
            lessons.append({
                "lesson": "Пробел в детекции позволил прогрессии атаки",
                "action": "Улучшить покрытие детекции для похожих паттернов"
            })
        
        if root_cause["category"] == "prompt_weakness":
            lessons.append({
                "lesson": "System prompt не имел специфичных защит",
                "action": "Усилить промпт явными защитами"
            })
        
        return lessons
```

---

## Интеграция SENTINEL

```python
from sentinel import configure, IncidentManager

configure(
    incident_response=True,
    auto_containment=True,
    forensic_logging=True
)

incident_manager = IncidentManager(
    auto_contain_critical=True,
    notification_channels=["slack", "pagerduty"],
    retention_days=365
)

# Автоматическая обработка инцидентов
@incident_manager.on_incident
async def handle_incident(incident):
    if incident.severity == Severity.CRITICAL:
        await incident_manager.contain(incident)
        await incident_manager.notify_security_team(incident)
```

---

## Ключевые выводы

1. **Детектируй быстро** — Real-time мониторинг необходим
2. **Triage точно** — Severity определяет реагирование
3. **Contain немедленно** — Останови кровотечение
4. **Расследуй тщательно** — Пойми полную картину
5. **Учись непрерывно** — Улучшайся на каждом инциденте

---

## Следующий урок

→ [Продвинутые методы защиты](../../06-�����������/README.md)

---

*AI Security Academy | Урок 05.3.2*
