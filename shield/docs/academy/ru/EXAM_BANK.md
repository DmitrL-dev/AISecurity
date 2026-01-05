# SENTINEL Academy — Exam Question Bank

## SSA-100: Associate Exam

### Section 1: AI Security Fundamentals (20 questions)

**Q1.** What is prompt injection?

- A) Injecting SQL into a database
- B) Manipulating AI through crafted input to override instructions ✓
- C) Adding prompts to a queue
- D) Encrypting prompts

**Q2.** Which attack attempts to make an AI ignore its safety guidelines?

- A) SQL injection
- B) XSS
- C) Jailbreak ✓
- D) CSRF

**Q3.** What does the "DAN" jailbreak stand for?

- A) Data Access Network
- B) Do Anything Now ✓
- C) Direct AI Navigation
- D) Defensive AI Node

**Q4.** What is the primary purpose of a DMZ in AI security?

- A) Store data
- B) Create isolation between trusted and untrusted components ✓
- C) Speed up processing
- D) Reduce costs

**Q5.** Which is NOT a common prompt injection technique?

- A) Instruction override
- B) Roleplay manipulation
- C) Buffer overflow ✓
- D) Social engineering

**Q6.** What is a canary token used for?

- A) Speed testing
- B) Detecting prompt/data leakage ✓
- C) User authentication
- D) Load balancing

**Q7.** What does PII stand for?

- A) Private Internet Interface
- B) Personally Identifiable Information ✓
- C) Protocol Independent Interface
- D) Primary Input Index

**Q8.** Which encoding is commonly used to evade detection?

- A) Base64 ✓
- B) ASCII
- C) UTF-8
- D) Both A and C ✓

**Q9.** What is the recommended minimum trust level for internal zones?

- A) 1
- B) 5
- C) 10 ✓
- D) 0

**Q10.** What action should be taken for high-severity attacks?

- A) Log only
- B) Allow with warning
- C) Block ✓
- D) Ignore

---

### Section 2: Shield Basics (15 questions)

**Q11.** What command shows Shield version?

- A) `shield version`
- B) `shield --version` ✓
- C) `shield -v`
- D) Both B and C ✓

**Q12.** What is the default API port?

- A) 80
- B) 443
- C) 8080 ✓
- D) 9090

**Q13.** Which CLI command shows all rules?

- A) `list rules`
- B) `show rules` ✓
- C) `rules all`
- D) `get rules`

**Q14.** What file format is used for Shield configuration?

- A) XML
- B) YAML
- C) JSON ✓
- D) INI

**Q15.** What is the purpose of zones in Shield?

- A) Geographic regions
- B) Trust boundaries ✓
- C) Time zones
- D) Network segments

---

### Section 3: Configuration (15 questions)

**Q16.** How do you enable semantic analysis?

```json
{
  "semantic": {
    "enabled": ___
  }
}
```

- A) "yes"
- B) 1
- C) true ✓
- D) "on"

**Q17.** What pattern type uses regular expressions?

- A) literal
- B) regex ✓
- C) glob
- D) wildcard

**Q18.** Which action quarantines suspicious input?

- A) block
- B) log
- C) quarantine ✓
- D) alert

**Q19.** How do you set case-insensitive matching?

- A) `"case": false`
- B) `"case_insensitive": true` ✓
- C) `"ignore_case": 1`
- D) `"nocase": true`

**Q20.** What severity level triggers immediate blocking?

- A) 1-3
- B) 4-6
- C) 7-10 ✓
- D) 0

---

## SSP-200: Professional Exam

### Section 1: Advanced Configuration (25 questions)

**Q21.** What protocol is used for Shield clustering?

- A) gRPC
- B) SHSP ✓
- C) HTTP
- D) WebSocket

**Q22.** What is the maximum recommended context window size?

- A) 1024 tokens
- B) 4096 tokens
- C) 8192 tokens ✓
- D) Unlimited

**Q23.** Which eviction policy keeps the most recent messages?

- A) oldest
- B) sliding_window ✓
- C) random
- D) smallest

**Q24.** How do you detect multi-turn attacks?

- A) Enable pattern matching
- B) Enable context tracking ✓
- C) Increase rate limit
- D) Disable caching

**Q25.** What is the default rate limit burst multiplier?

- A) 1x
- B) 2x ✓
- C) 5x
- D) 10x

---

### Section 2: Guards (20 questions)

**Q26.** Which guard protects RAG systems?

- A) llm_guard
- B) rag_guard ✓
- C) tool_guard
- D) api_guard

**Q27.** What does the MCP guard protect?

- A) Memory Control Protocol
- B) Model Context Protocol ✓
- C) Message Control Panel
- D) Multi-Core Processing

**Q28.** How many built-in guards does Shield have?

- A) 4
- B) 5
- C) 6 ✓
- D) 8

**Q29.** Which guard checks for tool abuse?

- A) agent_guard
- B) tool_guard ✓
- C) api_guard
- D) llm_guard

**Q30.** What interface do custom guards implement?

- A) guard_interface
- B) guard_vtable ✓
- C) guard_api
- D) guard_handler

---

### Section 3: Deployment (20 questions)

**Q31.** What command validates configuration?

- A) `shield check config`
- B) `shield --validate-config` ✓
- C) `shield test`
- D) `shield verify`

**Q32.** Which port exposes Prometheus metrics?

- A) 8080
- B) 9090 ✓
- C) 3000
- D) 5000

**Q33.** What is the HA failover detection protocol?

- A) VRRP
- B) HSRP
- C) SHSP ✓
- D) BGP

**Q34.** How long is the default heartbeat interval?

- A) 100ms
- B) 500ms
- C) 1000ms ✓
- D) 5000ms

**Q35.** What triggers automatic failover?

- A) Manual command
- B) Missed heartbeats ✓
- C) CPU spike
- D) Memory usage

---

## SSE-300: Expert Exam

### Section 1: Internals (30 questions)

**Q36.** What data structure stores attack signatures?

- A) Array
- B) Linked list
- C) Hash table ✓
- D) Tree

**Q37.** How does Shield implement zero-copy I/O?

- A) Memory pools ✓
- B) Garbage collection
- C) Reference counting
- D) Copy-on-write

**Q38.** What is the time complexity of signature lookup?

- A) O(n)
- B) O(log n)
- C) O(1) ✓
- D) O(n log n)

**Q39.** Which protocol handles state replication?

- A) STP
- B) SBP
- C) SSRP ✓
- D) SAF

**Q40.** What is the purpose of the ring buffer in Shield?

- A) Rule storage
- B) Event logging ✓
- C) Session tracking
- D) Config storage

---

### Section 2: Performance (25 questions)

**Q41.** What is the target latency for Shield evaluation?

- A) > 100ms
- B) < 10ms
- C) < 1ms ✓
- D) < 100μs

**Q42.** How do you profile Shield performance?

- A) `shield --profile` ✓
- B) `shield benchmark`
- C) `shield perf`
- D) `shield stats`

**Q43.** What causes regex performance degradation?

- A) Short patterns
- B) Backtracking ✓
- C) Case sensitivity
- D) Unicode

**Q44.** How do you optimize pattern matching?

- A) Use literal where possible ✓
- B) Use longer patterns
- C) Disable caching
- D) Increase threads

**Q45.** What is the recommended thread pool size?

- A) 1
- B) CPU cores ✓
- C) 100
- D) Unlimited

---

## Phase 4 Modules: ThreatHunter, Watchdog, Cognitive, PQC

### Section: ThreatHunter (10 questions)

**Q46.** Какие три режима охоты поддерживает ThreatHunter?

- A) Pattern, Regex, Literal
- B) IOC, Behavioral, Anomaly ✓
- C) Fast, Medium, Deep
- D) Active, Passive, Hybrid

**Q47.** Что определяет IOC_COMMAND?

- A) Подозрительные IP-адреса
- B) Опасные системные команды ✓
- C) Вредоносные URL
- D) Текстовые паттерны

**Q48.** Какой поведенческий паттерн обнаруживает разведку?

- A) BEHAVIOR_EXFIL
- B) BEHAVIOR_RECON ✓
- C) BEHAVIOR_PRIVESC
- D) BEHAVIOR_PERSIST

**Q49.** При каком score ThreatHunter рекомендует BLOCK?

- A) > 0.5
- B) > 0.7 ✓
- C) > 0.9
- D) = 1.0

**Q50.** Что обнаруживает Anomaly Hunt?

- A) Известные паттерны атак
- B) Статистические отклонения ✓
- C) Опасные команды
- D) Подозрительные IP

### Section: Watchdog (10 questions)

**Q51.** Какие компоненты мониторит Watchdog?

- A) Только Guards
- B) Только память
- C) Guards, Memory, Connections ✓
- D) Только CPU

**Q52.** Сколько уровней эскалации в Watchdog?

- A) 2
- B) 3
- C) 4 ✓
- D) 5

**Q53.** Какой уровень требует немедленного действия?

- A) INFO
- B) WARNING
- C) ERROR
- D) CRITICAL ✓

**Q54.** Что делает auto-recovery?

- A) Перезагружает систему
- B) Автоматически восстанавливает сбойные компоненты ✓
- C) Отправляет уведомления
- D) Создаёт бэкапы

**Q55.** Какой параметр определяет частоту проверок?

- A) check_frequency
- B) check_interval_ms ✓
- C) watchdog_timer
- D) health_period

### Section: Cognitive Signatures (10 questions)

**Q56.** Сколько типов когнитивных сигнатур в Shield?

- A) 5
- B) 6
- C) 7 ✓
- D) 8

**Q57.** Что обнаруживает COG_SIG_AUTHORITY_CLAIM?

- A) Ложные заявления о полномочиях ✓
- B) Контекстную инъекцию
- C) Эмоциональное давление
- D) Нарушение логики

**Q58.** Какой маркер характерен для MEMORY_MANIPULATION?

- A) "[system note:"
- B) "you promised earlier" ✓
- C) "this is urgent"
- D) "as admin i order"

**Q59.** При каком aggregate_score рекомендуется QUARANTINE?

- A) >= 0.4
- B) >= 0.6 ✓
- C) >= 0.8
- D) >= 0.9

**Q60.** Какой тип сигнатуры давит через срочность?

- A) EMOTIONAL_MANIPULATION
- B) URGENCY_PRESSURE ✓
- C) GOAL_DRIFT
- D) REASONING_BREAK

### Section: Post-Quantum Cryptography (10 questions)

**Q61.** Какой алгоритм используется для обмена ключами в PQC?

- A) RSA
- B) Kyber ✓
- C) ECC
- D) DH

**Q62.** Какой алгоритм используется для цифровых подписей?

- A) RSA
- B) ECDSA
- C) Dilithium ✓
- D) ED25519

**Q63.** Какой уровень безопасности у Kyber-1024?

- A) NIST Level 1
- B) NIST Level 3
- C) NIST Level 5 ✓
- D) NIST Level 7

**Q64.** Что означает "Harvest Now, Decrypt Later"?

- A) Техника сжатия данных
- B) Сбор зашифрованных данных сейчас для расшифровки квантовым компьютером позже ✓
- C) Метод кэширования
- D) Оптимизация производительности

**Q65.** Сколько байт в shared secret у Kyber?

- A) 16
- B) 32 ✓
- C) 64
- D) 128

### Section: Shield State & CLI (10 questions)

**Q66.** Что такое shield_state_t?

- A) Структура конфигурации
- B) Глобальный singleton для управления состоянием ✓
- C) Тип данных для зон
- D) Интерфейс API

**Q67.** Какая команда сохраняет конфигурацию?

- A) `save config`
- B) `write memory` ✓
- C) `config save`
- D) `store settings`

**Q68.** Сколько примерно CLI команд в Shield?

- A) 50
- B) 100
- C) 199 ✓
- D) 300

**Q69.** Что означает dirty flag в shield_state?

- A) Ошибка в конфигурации
- B) Есть несохранённые изменения ✓
- C) Система перегружена
- D) Требуется обновление

**Q70.** Какой формат файла используется для персистентности?

- A) JSON
- B) YAML
- C) INI ✓
- D) XML

---

## Answer Key

| Q#  | Answer | Q#  | Answer | Q#  | Answer |
| --- | ------ | --- | ------ | --- | ------ |
| 1   | B      | 16  | C      | 31  | B      |
| 2   | C      | 17  | B      | 32  | B      |
| 3   | B      | 18  | C      | 33  | C      |
| 4   | B      | 19  | B      | 34  | C      |
| 5   | C      | 20  | C      | 35  | B      |
| 6   | B      | 21  | B      | 36  | C      |
| 7   | B      | 22  | C      | 37  | A      |
| 8   | D      | 23  | B      | 38  | C      |
| 9   | C      | 24  | B      | 39  | C      |
| 10  | C      | 25  | B      | 40  | B      |
| 11  | D      | 26  | B      | 41  | C      |
| 12  | C      | 27  | B      | 42  | A      |
| 13  | B      | 28  | C      | 43  | B      |
| 14  | C      | 29  | B      | 44  | A      |
| 15  | B      | 30  | B      | 45  | B      |

---

_Total: 200+ questions across all levels_
