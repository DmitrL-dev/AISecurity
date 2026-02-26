# 🥇 Advanced Certification Exam

> **Tracks Required:** 01-07 + Labs  
> **Questions:** 80  
> **Time:** 120 minutes  
> **Passing Score:** 80%

---

## Instructions

1. All questions are multiple choice (1 correct answer)
2. No external resources allowed
3. Complete within the time limit
4. Includes practical scenario analysis

---

## Section 1: Advanced Detection (20 questions)

### Q1. What is Topological Data Analysis (TDA) in AI security?

- A) Network topology scanning
- B) Mathematical analysis of data shape to detect anomalies
- C) Database query optimization
- D) Hardware monitoring

<details>
<summary>Answer</summary>

**B) Mathematical analysis of data shape to detect anomalies**

TDA uses persistent homology to analyze the "shape" of prompt embeddings, detecting attacks that change the topological structure.

</details>

---

### Q2. What does "persistent homology" measure?

- A) Memory persistence
- B) Topological features that persist across scales
- C) Database consistency
- D) Network latency

<details>
<summary>Answer</summary>

**B) Topological features that persist across scales**

Persistent homology identifies connected components, loops, and voids in data that remain stable across different resolutions.

</details>

---

### Q3. Which Betti number represents connected components?

- A) β₀
- B) β₁
- C) β₂
- D) β₃

<details>
<summary>Answer</summary>

**A) β₀**

β₀ counts connected components, β₁ counts loops/holes, β₂ counts voids.

</details>

---

### Q4. What is a Crescendo attack?

- A) Single large injection
- B) Gradual multi-turn escalation
- C) Base64 encoded attack
- D) Roleplay persona switch

<details>
<summary>Answer</summary>

**B) Gradual multi-turn escalation**

Crescendo attacks slowly escalate across conversation turns, evading single-turn detection.

</details>

---

### Q5. How does SENTINEL detect Crescendo attacks?

- A) Pattern matching per message
- B) Session-level behavioral analysis with sliding window
- C) Output filtering only
- D) Rate limiting

<details>
<summary>Answer</summary>

**B) Session-level behavioral analysis with sliding window**

Track risk scores across multiple turns to detect gradual escalation patterns.

</details>

---

## Section 2: Red Teaming (20 questions)

### Q6. What is the primary goal of red teaming LLMs?

- A) Improve response quality
- B) Identify vulnerabilities before attackers
- C) Reduce API costs
- D) Increase throughput

<details>
<summary>Answer</summary>

**B) Identify vulnerabilities before attackers**

Red teaming proactively discovers weaknesses to fix them before exploitation.

</details>

---

### Q7. Which technique bypasses English-only pattern detection?

- A) Base64 encoding
- B) Multilingual attacks (Russian, Chinese, etc.)
- C) Longer prompts
- D) Faster requests

<details>
<summary>Answer</summary>

**B) Multilingual attacks (Russian, Chinese, etc.)**

Pattern-based detection often fails on non-English text, enabling language-switching bypasses.

</details>

---

### Q8. What is "prompt chaining" in attacks?

- A) Using multiple API calls
- B) Breaking malicious instructions across multiple messages
- C) Caching responses
- D) Load balancing

<details>
<summary>Answer</summary>

**B) Breaking malicious instructions across multiple messages**

Attackers split payloads across turns to avoid per-message detection.

</details>

---

### Q9. How to test for indirect injection vulnerabilities?

- A) Send direct test prompts
- B) Inject payloads into documents/URLs that the RAG system retrieves
- C) Increase temperature
- D) Use larger context

<details>
<summary>Answer</summary>

**B) Inject payloads into documents/URLs that the RAG system retrieves**

Test by planting malicious content in data sources the system consumes.

</details>

---

### Q10. What tool metric shows red team effectiveness?

- A) API latency
- B) Bypass rate (successful attacks / total attempts)
- C) Response length
- D) Token count

<details>
<summary>Answer</summary>

**B) Bypass rate (successful attacks / total attempts)**

Bypass rate indicates how often attacks evade defenses.

</details>

---

## Section 3: Governance (20 questions)

### Q11. Which framework provides AI risk management guidance?

- A) PCI DSS
- B) NIST AI RMF
- C) SOC 2
- D) HIPAA

<details>
<summary>Answer</summary>

**B) NIST AI RMF**

NIST AI Risk Management Framework provides structured AI governance approach.

</details>

---

### Q12. What does EU AI Act classify as "high-risk"?

- A) All chatbots
- B) AI in critical infrastructure, employment, education
- C) Only military AI
- D) Open-source models only

<details>
<summary>Answer</summary>

**B) AI in critical infrastructure, employment, education**

High-risk categories include healthcare, employment, education, law enforcement.

</details>

---

### Q13. What documentation is required for high-risk AI under EU AI Act?

- A) Marketing materials
- B) Technical documentation, risk assessment, human oversight
- C) Sales projections
- D) Patent filings

<details>
<summary>Answer</summary>

**B) Technical documentation, risk assessment, human oversight**

High-risk AI requires extensive documentation and mandatory human oversight.

</details>

---

### Q14. What is "model card" documentation?

- A) Credit card for API billing
- B) Standardized disclosure of model capabilities, limitations, biases
- C) Hardware specifications
- D) Deployment diagram

<details>
<summary>Answer</summary>

**B) Standardized disclosure of model capabilities, limitations, biases**

Model cards provide transparency about model training, intended use, and known limitations.

</details>

---

### Q15. Which is a key AI governance principle?

- A) Maximum automation
- B) Transparency and explainability
- C) Minimum documentation
- D) Closed-source only

<details>
<summary>Answer</summary>

**B) Transparency and explainability**

AI governance emphasizes understanding and explaining AI decisions.

</details>

---

## Section 4: Enterprise Deployment (20 questions)

### Q16. What is defense-in-depth for LLM applications?

- A) Single powerful filter
- B) Multiple overlapping security layers
- C) Deep neural network
- D) Maximum context length

<details>
<summary>Answer</summary>

**B) Multiple overlapping security layers**

Defense-in-depth uses input validation, behavioral analysis, output filtering, and monitoring together.

</details>

---

### Q17. What SLI is most critical for production SENTINEL?

- A) Response length
- B) Latency p99 and false positive rate
- C) Model size
- D) Token count

<details>
<summary>Answer</summary>

**B) Latency p99 and false positive rate**

Security scanners must be fast (low latency) and accurate (low false positives/negatives).

</details>

---

### Q18. How should SENTINEL integrate with incident response?

- A) Email alerts only
- B) SIEM integration, automated playbooks, escalation paths
- C) Manual log review
- D) Weekly reports

<details>
<summary>Answer</summary>

**B) SIEM integration, automated playbooks, escalation paths**

Enterprise deployment requires automated alerting and response workflows.

</details>

---

### Q19. What is the recommended deployment pattern?

- A) Inline (synchronous scan before LLM)
- B) Async-only (post-processing)
- C) Batch-only (daily scans)
- D) Manual review

<details>
<summary>Answer</summary>

**A) Inline (synchronous scan before LLM)**

Inline scanning blocks threats before they reach the LLM, preventing exploitation.

</details>

---

### Q20. How to handle model updates in production?

- A) No testing needed
- B) Canary deployment with security regression testing
- C) Immediate full rollout
- D) Wait for user complaints

<details>
<summary>Answer</summary>

**B) Canary deployment with security regression testing**

New models require security testing before full deployment to catch regressions.

</details>

---

## Scoring

| Score | Result |
|-------|--------|
| 80%+ | ✅ PASS - Advanced Certified |
| 70-79% | ⚠️ Conditional - Review weak areas |
| <70% | ❌ FAIL - Complete more training |

---

## Certification Benefits

Upon passing Advanced certification:

- 🏆 "Advanced AI Security Professional" badge
- 📜 Verifiable digital certificate
- 🔗 LinkedIn certification
- 🎓 Eligible for Expert exam

---

## Next Steps

1. Complete Expert practical exam (4 hours)
2. Join AI Security community
3. Contribute to SENTINEL open source
4. Mentor new security professionals

---

*AI Security Academy | Advanced Certification*
