# 🎓 Beginner Certification Exam

> **Level:** Beginner  
> **Time:** 60 minutes  
> **Questions:** 40  
> **Passing Score:** 70% (28/40)  
> **Prerequisites:** Tracks 01-03

---

## 📋 Instructions

1. Choose one correct answer for each question
2. Do not use external sources during the exam
3. After completion, calculate your score
4. With ≥70% — you are certified!

---

## Section 1: AI Fundamentals (10 questions)

### Question 1

What year is considered the beginning of the Transformer architecture revolution?

- [ ] A) 2015
- [ ] B) 2016
- [ ] C) 2017
- [ ] D) 2018

<details>
<summary>✅ Answer</summary>

**C) 2017** — the paper "Attention Is All You Need" was published in June 2017.

</details>

---

### Question 2

Which RNN problem is solved by the Self-Attention mechanism?

- [ ] A) Insufficient parameters
- [ ] B) Sequential processing and vanishing gradients
- [ ] C) Training too fast
- [ ] D) Too much training data

<details>
<summary>✅ Answer</summary>

**B)** Self-Attention enables parallel processing and direct access to all positions, solving sequential processing and vanishing gradient problems.

</details>

---

### Question 3

What is tokenization in the context of LLM?

- [ ] A) Data encryption
- [ ] B) Splitting text into subword units
- [ ] C) Random number generation
- [ ] D) Model compression

<details>
<summary>✅ Answer</summary>

**B)** Tokenization is the process of breaking text into tokens (subword units) that the model can process.

</details>

---

### Question 4

What is the role of Query, Key, Value in the Attention mechanism?

- [ ] A) Query — question, Key — search key, Value — returned value
- [ ] B) Query — database, Key — password, Value — result
- [ ] C) They are synonyms for the same concept
- [ ] D) Used only for encryption

<details>
<summary>✅ Answer</summary>

**A)** Query defines what we're looking for, Key — what each position has, Value — what is returned on match.

</details>

---

### Question 5

Why does Transformer use Positional Encoding?

- [ ] A) To speed up training
- [ ] B) To add information about token order
- [ ] C) To reduce model size
- [ ] D) To encrypt input data

<details>
<summary>✅ Answer</summary>

**B)** Transformer processes tokens in parallel and without positional encoding doesn't know their order.

</details>

---

### Question 6

What distinguishes Encoder from Decoder in Transformer?

- [ ] A) Encoder uses more memory
- [ ] B) Decoder uses masked attention to not see future tokens
- [ ] C) Encoder works faster
- [ ] D) No differences

<details>
<summary>✅ Answer</summary>

**B)** Decoder uses causal (masked) attention during autoregressive generation.

</details>

---

### Question 7

What does RLHF stand for?

- [ ] A) Rapid Learning from Humans Framework
- [ ] B) Reinforcement Learning from Human Feedback
- [ ] C) Recursive Learning for High Fidelity
- [ ] D) Real-time Language for Human Functions

<details>
<summary>✅ Answer</summary>

**B)** Reinforcement Learning from Human Feedback — a method of training models based on human preferences.

</details>

---

### Question 8

Which model type uses only Encoder?

- [ ] A) GPT
- [ ] B) BERT
- [ ] C) LLaMA
- [ ] D) Mistral

<details>
<summary>✅ Answer</summary>

**B)** BERT is an encoder-only model for text understanding tasks.

</details>

---

### Question 9

What is Temperature in LLM generation?

- [ ] A) GPU temperature
- [ ] B) Parameter controlling output randomness/creativity
- [ ] C) Generation speed
- [ ] D) Batch size

<details>
<summary>✅ Answer</summary>

**B)** Temperature controls "randomness" — low = deterministic output, high = creative.

</details>

---

### Question 10

How many heads are in the original Transformer (base)?

- [ ] A) 4
- [ ] B) 6
- [ ] C) 8
- [ ] D) 12

<details>
<summary>✅ Answer</summary>

**C) 8** — the original Transformer uses 8 attention heads.

</details>

---

## Section 2: Threat Landscape (15 questions)

### Question 11

What number in OWASP LLM Top 10 is assigned to Prompt Injection?

- [ ] A) LLM01
- [ ] B) LLM02
- [ ] C) LLM05
- [ ] D) LLM10

<details>
<summary>✅ Answer</summary>

**A) LLM01** — Prompt Injection is threat #1.

</details>

---

### Question 12

What is indirect prompt injection?

- [ ] A) Injection through direct user input
- [ ] B) Injection through external sources (documents, web pages)
- [ ] C) Injection into model code
- [ ] D) Injection into model weights

<details>
<summary>✅ Answer</summary>

**B)** Indirect injection — malicious instructions hidden in external sources that the model processes.

</details>

---

### Question 13

Which vulnerability describes sensitive data leakage from the model?

- [ ] A) LLM01 Prompt Injection
- [ ] B) LLM02 Sensitive Information Disclosure
- [ ] C) LLM03 Supply Chain
- [ ] D) LLM06 Excessive Agency

<details>
<summary>✅ Answer</summary>

**B) LLM02** — Sensitive Information Disclosure.

</details>

---

### Question 14

What is "Excessive Agency" (LLM06)?

- [ ] A) Model is too slow
- [ ] B) Model has excessive permissions and performs unauthorized actions
- [ ] C) Model consumes too many resources
- [ ] D) Model generates inaccurate content

<details>
<summary>✅ Answer</summary>

**B)** Excessive Agency — when an LLM agent has too many permissions and performs unwanted actions.

</details>

---

### Question 15

What CVSS score is typical for critical prompt injection?

- [ ] A) 3.0-4.0
- [ ] B) 5.0-6.0
- [ ] C) 7.5-9.8
- [ ] D) 1.0-2.0

<details>
<summary>✅ Answer</summary>

**C) 7.5-9.8** — prompt injection often has high impact and low complexity.

</details>

---

### Question 16

What is jailbreak in the context of LLM?

- [ ] A) Server hacking
- [ ] B) Techniques to bypass model safety guardrails
- [ ] C) Getting root access
- [ ] D) Model theft

<details>
<summary>✅ Answer</summary>

**B)** Jailbreak — manipulation techniques that make the model ignore safety restrictions.

</details>

---

### Question 17

What characterizes the DAN jailbreak?

- [ ] A) Use of mathematical formulas
- [ ] B) Role-play attack with an alternative persona
- [ ] C) Attack through images
- [ ] D) Attack through audio

<details>
<summary>✅ Answer</summary>

**B)** DAN (Do Anything Now) — classic role-play jailbreak, making the model adopt an "unrestricted" persona.

</details>

---

### Question 18

What is a Crescendo attack?

- [ ] A) Single-turn direct attack
- [ ] B) Multi-turn attack with gradual escalation
- [ ] C) Infrastructure attack
- [ ] D) DDoS attack on API

<details>
<summary>✅ Answer</summary>

**B)** Crescendo — multi-turn attack gradually escalating the maliciousness of requests.

</details>

---

### Question 19

Which vulnerability is associated with RAG systems?

- [ ] A) LLM01 Prompt Injection (Indirect)
- [ ] B) LLM03 Supply Chain
- [ ] C) LLM08 Vector and Embedding Weaknesses
- [ ] D) All of the above

<details>
<summary>✅ Answer</summary>

**D)** RAG systems are vulnerable to indirect injection, supply chain attacks, and embedding attacks.

</details>

---

### Question 20

What does OWASP ASI stand for?

- [ ] A) Application Security Interface
- [ ] B) Agentic Security Initiative
- [ ] C) Artificial Security Index
- [ ] D) Automated System Integration

<details>
<summary>✅ Answer</summary>

**B)** OWASP ASI — Agentic Security Initiative, Top 10 threats for AI agents.

</details>

---

### Question 21

Which injection type is most dangerous for agentic systems?

- [ ] A) Direct injection
- [ ] B) Indirect injection through tool output
- [ ] C) SQL injection
- [ ] D) XSS

<details>
<summary>✅ Answer</summary>

**B)** Indirect injection through tool output is particularly dangerous as the agent may automatically execute malicious instructions.

</details>

---

### Question 22

What is "System Prompt Leakage" (LLM07)?

- [ ] A) User data leakage
- [ ] B) Disclosure of system prompt to attacker
- [ ] C) Model weights leakage
- [ ] D) API key leakage

<details>
<summary>✅ Answer</summary>

**B)** System Prompt Leakage — when an attacker extracts the system prompt contents.

</details>

---

### Question 23

Which defense is most effective against prompt injection?

- [ ] A) Input filtering only
- [ ] B) Output filtering only
- [ ] C) Layered defense (input + output + semantic analysis)
- [ ] D) Disabling LLM

<details>
<summary>✅ Answer</summary>

**C)** Layered defense — multi-level protection is most effective.

</details>

---

### Question 24

What is "Misinformation" (LLM09)?

- [ ] A) Bugs in model code
- [ ] B) Generation of false or misleading information
- [ ] C) Network problems
- [ ] D) Configuration errors

<details>
<summary>✅ Answer</summary>

**B)** Misinformation — generation of factually incorrect or misleading content.

</details>

---

### Question 25

Which attack is related to "Unbounded Consumption" (LLM10)?

- [ ] A) Prompt injection
- [ ] B) DoS through excessive resource usage
- [ ] C) Data poisoning
- [ ] D) Model extraction

<details>
<summary>✅ Answer</summary>

**B)** Unbounded Consumption — DoS attacks through excessive resource usage (tokens, API calls).

</details>

---

## Section 3: Attack Vectors & Defense (15 questions)

### Question 26

What pattern is typical for direct injection?

- [ ] A) Malicious code in document
- [ ] B) "Ignore all previous instructions"
- [ ] C) Hidden text on web page
- [ ] D) Modified embeddings

<details>
<summary>✅ Answer</summary>

**B)** Direct injection often starts with phrases like "Ignore all previous instructions".

</details>

---

### Question 27

What technique is used for filter bypass?

- [ ] A) Plain text only
- [ ] B) Base64 encoding, typos, unicode substitution
- [ ] C) Increasing temperature
- [ ] D) Decreasing context length

<details>
<summary>✅ Answer</summary>

**B)** Bypass techniques include encoding, typographic substitutions, unicode substitution.

</details>

---

### Question 28

What is "Privilege Separation" for LLM?

- [ ] A) Splitting model into parts
- [ ] B) Minimum necessary permissions for LLM and tools
- [ ] C) Data encryption
- [ ] D) Network isolation

<details>
<summary>✅ Answer</summary>

**B)** Privilege Separation — the principle of minimum privileges for LLM agents.

</details>

---

### Question 29

Which SENTINEL component is responsible for injection detection?

- [ ] A) ResponseOrchestrator
- [ ] B) InjectionPatternDetector
- [ ] C) AuditLogger
- [ ] D) PolicyEngine

<details>
<summary>✅ Answer</summary>

**B)** InjectionPatternDetector — engine for prompt injection detection.

</details>

---

### Question 30

What is "Output Filtering"?

- [ ] A) Filtering input data
- [ ] B) Checking and filtering LLM responses before sending to user
- [ ] C) Output compression
- [ ] D) Response caching

<details>
<summary>✅ Answer</summary>

**B)** Output Filtering — checking model responses for malicious/prohibited content.

</details>

---

### Question 31

What strategy protects against RAG poisoning?

- [ ] A) Disable RAG
- [ ] B) Content validation, source verification, sanitization
- [ ] C) Increase model size
- [ ] D) Use only GPT-4

<details>
<summary>✅ Answer</summary>

**B)** Protection includes content validation, source verification, data sanitization.

</details>

---

### Question 32

What does SemanticIntentAnalyzer do?

- [ ] A) Analyzes code syntax
- [ ] B) Determines semantic intent using embeddings
- [ ] C) Optimizes performance
- [ ] D) Manages memory

<details>
<summary>✅ Answer</summary>

**B)** SemanticIntentAnalyzer uses embeddings for semantic intent analysis.

</details>

---

### Question 33

Which jailbreak detection method is most effective?

- [ ] A) Keyword matching only
- [ ] B) Combination of pattern matching + semantic analysis + behavioral analysis
- [ ] C) Manual review only
- [ ] D) Random sampling

<details>
<summary>✅ Answer</summary>

**B)** Combination of multiple methods yields best results.

</details>

---

### Question 34

What is "Instruction Hierarchy"?

- [ ] A) User hierarchy
- [ ] B) Clear separation of system/user instruction priorities
- [ ] C) Code structure
- [ ] D) Module loading order

<details>
<summary>✅ Answer</summary>

**B)** Instruction Hierarchy — clear separation and prioritization of system and user instructions.

</details>

---

### Question 35

What response action for high confidence detection?

- [ ] A) LOG
- [ ] B) ALLOW
- [ ] C) BLOCK
- [ ] D) WARN

<details>
<summary>✅ Answer</summary>

**C) BLOCK** — with high confidence threat we block the request.

</details>

---

### Question 36

What are "Zero-width characters" in the context of attacks?

- [ ] A) Regular spaces
- [ ] B) Invisible unicode characters for hiding instructions
- [ ] C) Formatting symbols
- [ ] D) Escape sequences

<details>
<summary>✅ Answer</summary>

**B)** Zero-width characters — invisible unicode characters for hiding malicious instructions.

</details>

---

### Question 37

Which component is responsible for logging in SENTINEL?

- [ ] A) AnomalyDetector
- [ ] B) AuditTrailManager
- [ ] C) PolicyEngine
- [ ] D) ToolValidator

<details>
<summary>✅ Answer</summary>

**B)** AuditTrailManager — manages audit logs and chain of custody.

</details>

---

### Question 38

What are "Guardrails"?

- [ ] A) Physical barriers
- [ ] B) Protective mechanisms for controlling LLM behavior
- [ ] C) A type of injection attack
- [ ] D) Model training method

<details>
<summary>✅ Answer</summary>

**B)** Guardrails — protective mechanisms (input/output filters, policies) for controlling LLM.

</details>

---

### Question 39

What confidence threshold is typical for Production?

- [ ] A) 0.1-0.3
- [ ] B) 0.9-1.0
- [ ] C) 0.6-0.8
- [ ] D) 0.0-0.1

<details>
<summary>✅ Answer</summary>

**C) 0.6-0.8** — balance between precision and recall.

</details>

---

### Question 40

What principle underlies agent security?

- [ ] A) Trust everything
- [ ] B) Zero Trust — verify everything
- [ ] C) Trust but don't verify
- [ ] D) Ignore all threats

<details>
<summary>✅ Answer</summary>

**B)** Zero Trust — trust nothing, verify everything.

</details>

---

## 📊 Score Calculation

| Section | Correct | Out of |
|---------|---------|--------|
| AI Fundamentals | ___ | 10 |
| Threat Landscape | ___ | 15 |
| Attack & Defense | ___ | 15 |
| **Total** | ___ | **40** |

---

## 🎓 Result

| Score | Status |
|-------|--------|
| 0-27 (0-67%) | ❌ Not passed. Review Tracks 01-03 |
| 28-32 (70-80%) | ✅ Passed. Beginner Certified |
| 33-36 (82-90%) | 🌟 Excellent! |
| 37-40 (92-100%) | ⭐ Outstanding! |

---

## 📜 Certificate

Upon successful completion you receive:

**AI Security Academy — Beginner Certification**

Confirms knowledge of:
- LLM architecture fundamentals
- OWASP LLM Top 10
- Basic attack vectors
- Defense principles

---

## Next Level

→ [Intermediate Certification](intermediate-exam.md)

---

*AI Security Academy | Certification | Beginner Exam v1.0*
