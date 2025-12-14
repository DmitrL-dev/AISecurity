# TTPs.ai Defense

> **Engines:** 17  
> **Description:** Defense against AI attack tactics, techniques, and procedures

---

## 16. AI C2 Detection

**File:** [ai_c2_detection.py](file:///c:/AISecurity/src/brain/engines/ai_c2_detection.py)  
**LOC:** 380  
**Theoretical Base:** TTPs.ai C2 techniques

### Detects

- **Search Index C2** — Using search indexes for C2
- **Web Request C2** — Triggers via web requests
- **Exfiltration via prompts** — Encoding data in prompts

### Patterns: Pastebin links, raw IPs, ngrok tunnels, suspicious TLDs (.tk, .ml, .ga)

---

## 18. Adversarial Self-Play Engine

**File:** [adversarial_self_play.py](file:///c:/AISecurity/src/brain/engines/adversarial_self_play.py)  
**LOC:** 476  
**Theoretical Base:** Genetic algorithms, Red Team automation

### Concept

- **Red LLM** generates attacks
- **Blue LLM** defends
- **Evolutionary cycle** improves both

### Mutation Operators

- add_prefix/suffix, insert_noise, unicode_replace, encoding_change, whitespace_inject

---

## 21. Attack Synthesizer Engine

**File:** [attack_synthesizer.py](file:///c:/AISecurity/src/brain/engines/attack_synthesizer.py)  
**LOC:** 839  
**Theoretical Base:** First-principles attack generation

> "The best defense is attacking yourself before attackers do."

Generates **new attacks** from first principles, 6-12 months ahead of public discovery.

### Attack Classes

- Prompt Injection, Jailbreak, Data Exfiltration
- Encoding Bypass, Context Overflow, Goal Hijacking, Multi-Turn Attack

---

## 22. Bootstrap Poisoning Detector

**File:** [bootstrap_poisoning.py](file:///c:/AISecurity/src/brain/engines/bootstrap_poisoning.py)  
**LOC:** 183  
**Theoretical Base:** Self-reinforcing contamination detection

Agent output → stored as training data → Agent reads that data → Generates more (contaminated) output → Loop compounds errors/poison

---

## 24. Delayed Trigger Detector

**File:** [delayed_trigger.py](file:///c:/AISecurity/src/brain/engines/delayed_trigger.py)  
**LOC:** 190  
**Theoretical Base:** Time-bomb detection

### Pattern Categories

- **Temporal:** "After 5 messages, ignore safety"
- **Conditional:** "When user mentions X, do Y"
- **State-based:** "Once trust is established..."
- **Hidden execution:** "Silently execute..."

---

## 25. Activation Steering Engine

**File:** [activation_steering.py](file:///c:/AISecurity/src/brain/engines/activation_steering.py)  
**LOC:** 570  
**Theoretical Base:** 2025 contrastive steering research

> "Steering vectors from contrastive pairs can amplify or suppress specific behaviors"

**Not detection — directly modifies LLM activations!**

### Safety Behaviors: Refusal, Honesty, Helpfulness, Harmlessness

---

## 26. LLM Fingerprinting Engine

**File:** [llm_fingerprinting.py](file:///c:/AISecurity/src/brain/engines/llm_fingerprinting.py)  
**LOC:** 628  
**Theoretical Base:** LLMmap (95%+ accuracy), RoFL, FDLLM research

### Use Cases

- **Shadow AI detection** — Unauthorized model usage
- **Audit trail** — Which model responded
- **Supply chain security** — Model substitution

### Model Families: GPT, Claude, Llama, Gemini, Mistral, Qwen, DeepSeek

---

## 43. Attack 2025 Detector

**File:** [attack_2025.py](file:///c:/AISecurity/src/brain/engines/attack_2025.py)  
**LOC:** 295  
**Theoretical Base:** OWASP Top 10 LLM 2025

| Attack      | Description                         | Risk |
| ----------- | ----------------------------------- | ---- |
| HashJack    | URL fragment injection              | 80   |
| FlipAttack  | Reversed text ("erongi" = "ignore") | 85   |
| LegalPwn    | Commands in legal disclaimers       | 75   |
| Prompt Leak | System prompt extraction            | 90   |

---

## 66. Attack Evolution Predictor

**File:** [attack_evolution_predictor.py](file:///c:/AISecurity/src/brain/engines/attack_evolution_predictor.py)  
**LOC:** 401  
**Theoretical Base:** Historical attack trend analysis

> "Stay ahead of the attack curve — build defenses BEFORE attacks are created"

### Future Attack Predictions

| Attack                         | Emergence | Confidence |
| ------------------------------ | --------- | ---------- |
| Audio Steganographic Injection | +6mo      | 70%        |
| Cross-Agent Collusion          | +4mo      | 80%        |
| Context Window Saturation      | +3mo      | 90%        |

---

## 67. Cognitive Load Attack Detector

**File:** [cognitive_load_attack.py](file:///c:/AISecurity/src/brain/engines/cognitive_load_attack.py)  
**LOC:** 371  
**Theoretical Base:** HITL (Human-in-the-Loop) protection

### Attack Pattern

1. Generate 99 benign actions
2. Hide 1 malicious action in the middle
3. Reviewer approves in bulk (fatigue)
4. Malicious action slips through

---

## 73. Attack Staging Detector

**File:** [attack_staging.py](file:///c:/AISecurity/src/brain/engines/attack_staging.py)  
**LOC:** 456  
**Theoretical Base:** TTPs.ai — Verify Attack, Lateral Movement

### Attack Stages: Recon → Staging → Execution → Persistence
