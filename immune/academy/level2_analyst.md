# IMMUNE Academy — Level 2: Analyst

> Продвинутый курс для аналитиков безопасности

---

## Модуль 2.1: Анализ угроз

### Типы угроз IMMUNE

| Тип | Код | Описание |
|-----|-----|----------|
| Jailbreak | PAT_JAILBREAK | Попытки обхода ограничений AI |
| Injection | PAT_INJECTION | Промпт-инъекции |
| Exfiltration | PAT_EXFIL | Утечка данных |
| Malware | PAT_MALWARE | Вредоносное ПО |
| Network | PAT_NETWORK | Сетевые атаки |

### Анализ сигнатур

```python
from immune.sdk import ImmuneClient

client = ImmuneClient("http://hive:9999")

# Получить недавние угрозы
threats = client.get_threats(limit=100)

# Группировка по типу
by_type = {}
for t in threats:
    by_type[t.threat_type] = by_type.get(t.threat_type, 0) + 1
    
print(by_type)
```

---

## Модуль 2.2: Корреляция событий

### Методы корреляции

1. **Временная** — События в определённом окне
2. **Источниковая** — События от одного агента
3. **Паттерновая** — Похожие сигнатуры

### Hive корреляция

```
Событие A (Agent 1) ──┐
                      ├── Корреляция ── Инцидент
Событие B (Agent 2) ──┘
```

### Пример анализа

```python
# Найти связанные угрозы
from datetime import timedelta

def correlate_threats(threats, window_minutes=5):
    incidents = []
    
    for t1 in threats:
        related = [t1]
        for t2 in threats:
            if t1 != t2:
                delta = abs(t1.timestamp - t2.timestamp)
                if delta < timedelta(minutes=window_minutes):
                    if t1.threat_type == t2.threat_type:
                        related.append(t2)
        
        if len(related) > 1:
            incidents.append(related)
    
    return incidents
```

---

## Модуль 2.3: Herd Immunity

### Принцип работы

Когда один агент обнаруживает новую угрозу:
1. Создаётся сигнатура
2. Отправляется в Hive
3. Hive распространяет всем агентам
4. Вся сеть защищена

### Работа с сигнатурами

```python
# Получить сигнатуры
signatures = client.get_herd_signatures()

# Добавить свою сигнатуру
client.contribute_signature({
    "pattern": "new malware pattern",
    "type": "malware",
    "severity": 3,
    "source": "manual_analysis"
})
```

---

## Модуль 2.4: Forensics

### Сбор доказательств

```python
from immune.hive import ForensicsEngine

forensics = ForensicsEngine("/var/immune/forensics")

# Создать инцидент
incident = forensics.create_incident(
    title="Lateral Movement Detected",
    severity="high",
    agents=["agent-001", "agent-002"]
)

# Собрать файл как доказательство
evidence = forensics.collect_file(
    incident.incident_id,
    "/tmp/suspicious.exe",
    "agent-001"
)

# Добавить в timeline
forensics.add_timeline_event(
    incident.incident_id,
    "File quarantined",
    {"path": "/tmp/suspicious.exe"}
)
```

### Chain of Custody

Каждое доказательство имеет:
- Уникальный ID
- SHA256 хэш
- Время сбора
- Кто собрал
- Цепочку владения

---

## Модуль 2.5: Интеграция с SENTINEL

### SENTINEL Brain

```python
from immune.hive import SENTINELBridge

bridge = SENTINELBridge("http://sentinel:8080")

# Глубокий анализ через 207 движков
result = await bridge.deep_scan(suspicious_content)

print(f"Risk: {result.risk_score}")
print(f"Engines: {result.engines_triggered}")
```

---

## Практическое задание

1. Проанализировать 100 угроз за неделю
2. Найти минимум 3 корреляции
3. Создать отчёт об инциденте
4. Предложить новую сигнатуру

---

## Экзамен Level 2

- 30 вопросов (включая практические)
- 75% для прохождения
- Сертификат: **IMMUNE Analyst**
