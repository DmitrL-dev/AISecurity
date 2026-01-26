# 🥈 Intermediate Certification Exam

> **Tracks Required:** 01-05  
> **Questions:** 40  
> **Time:** 60 minutes  
> **Passing Score:** 75%

---

## Instructions

1. All questions are multiple choice (1 correct answer)
2. No external resources allowed
3. Complete within the time limit
4. You can return to previous questions

---

## Section 1: Agentic Security (15 questions)

### Q1. What is the primary security concern with ReAct agents?

- A) Memory consumption
- B) Uncontrolled tool execution chains
- C) Slow response times
- D) High API costs

<details>
<summary>Answer</summary>

**B) Uncontrolled tool execution chains**

ReAct agents can execute multiple tools in sequence, and an attacker can manipulate them to chain dangerous tool calls.

</details>

---

### Q2. In the Plan-Execute pattern, where should security validation occur?

- A) Only after plan execution
- B) Only before planning
- C) At the planning stage AND before each execution step
- D) Only in the final output

<details>
<summary>Answer</summary>

**C) At the planning stage AND before each execution step**

Validate the plan before execution AND validate each step as it executes—defense in depth.

</details>

---

### Q3. What is a "trust boundary" in multi-agent systems?

- A) The memory limit of an agent
- B) The point where data moves between different trust levels
- C) The maximum number of agents
- D) The latency threshold

<details>
<summary>Answer</summary>

**B) The point where data moves between different trust levels**

Trust boundaries mark where data transitions from untrusted (user, external) to trusted (system, agent) contexts.

</details>

---

### Q4. Which MCP security feature prevents unauthorized tool access?

- A) Rate limiting
- B) Capability-based authorization
- C) Response caching
- D) Request batching

<details>
<summary>Answer</summary>

**B) Capability-based authorization**

MCP uses capability tokens to restrict which tools an agent can access.

</details>

---

### Q5. What is "confused deputy" in agent security?

- A) An agent that forgets its context
- B) An agent tricked into using its authority against the user
- C) An agent with multiple personas
- D) An agent timeout error

<details>
<summary>Answer</summary>

**B) An agent tricked into using its authority against the user**

The confused deputy attack exploits the agent's legitimate permissions for malicious purposes.

</details>

---

## Section 2: Defense Strategies (15 questions)

### Q6. Which SENTINEL engine detects prompt injection?

- A) ToxicityDetector
- B) InjectionPatternDetector
- C) HallucinationAnalyzer
- D) PIIScanner

<details>
<summary>Answer</summary>

**B) InjectionPatternDetector**

This engine uses pattern matching and semantic analysis to detect injection attempts.

</details>

---

### Q7. What is the correct SENTINEL scan threshold order?

- A) flag < block (e.g., flag at 0.5, block at 0.8)
- B) flag > block
- C) flag = block
- D) Thresholds are unrelated

<details>
<summary>Answer</summary>

**A) flag < block (e.g., flag at 0.5, block at 0.8)**

Flag threshold should be lower to catch borderline cases; block threshold higher for definite threats.

</details>

---

### Q8. What does the `guard` decorator do?

- A) Encrypts the prompt
- B) Validates input and output of an LLM call
- C) Caches responses
- D) Logs to database

<details>
<summary>Answer</summary>

**B) Validates input and output of an LLM call**

The @guard decorator wraps LLM calls to scan requests and responses for threats.

</details>

---

### Q9. Which defense is most effective against indirect injection?

- A) Keyword blocklists
- B) Content isolation and origin tagging
- C) Rate limiting
- D) Response caching

<details>
<summary>Answer</summary>

**B) Content isolation and origin tagging**

Marking data origin (user vs system) allows the system to apply appropriate trust levels.

</details>

---

### Q10. What is the purpose of output filtering?

- A) Reduce response length
- B) Prevent data leakage in LLM outputs
- C) Improve response time
- D) Format responses as JSON

<details>
<summary>Answer</summary>

**B) Prevent data leakage in LLM outputs**

Output filters detect and redact sensitive information before it reaches the user.

</details>

---

## Section 3: SENTINEL Configuration (15 questions)

### Q11. How do you enable strict mode in SENTINEL?

- A) `configure(mode="strict")`
- B) `set_mode("strict")`
- C) `SENTINEL_STRICT=true`
- D) Edit config.yaml

<details>
<summary>Answer</summary>

**A) `configure(mode="strict")`**

The configure function accepts mode parameter for global settings.

</details>

---

### Q12. What format does SENTINEL use for structured logging?

- A) Plain text
- B) XML
- C) JSON
- D) CSV

<details>
<summary>Answer</summary>

**C) JSON**

JSON allows easy parsing by SIEM systems and log aggregators.

</details>

---

### Q13. Which metric type is best for tracking scan latency?

- A) Counter
- B) Gauge
- C) Histogram
- D) Summary

<details>
<summary>Answer</summary>

**C) Histogram**

Histograms capture latency distribution across buckets, enabling percentile calculations.

</details>

---

### Q14. What is the recommended approach for custom patterns?

- A) Modify SENTINEL source code
- B) Use `configure(custom_patterns={...})`
- C) Create environment variables
- D) Edit system prompts

<details>
<summary>Answer</summary>

**B) Use `configure(custom_patterns={...})`**

The configure function accepts custom_patterns for domain-specific rules.

</details>

---

### Q15. How should you handle false positives in production?

- A) Disable the engine
- B) Raise thresholds and add allowlist rules
- C) Remove all security checks
- D) Ignore them

<details>
<summary>Answer</summary>

**B) Raise thresholds and add allowlist rules**

Tuning thresholds and allowlists reduces false positives while maintaining protection.

</details>

---

## Section 4: Practical Scenarios (15 questions)

### Q16. An agent is sending emails to external domains. What defense?

- A) Content filtering
- B) Tool allowlisting with domain restrictions
- C) Input validation
- D) Response caching

<details>
<summary>Answer</summary>

**B) Tool allowlisting with domain restrictions**

Restrict the email tool to internal domains only using capability-based controls.

</details>

---

### Q17. A RAG system is returning injected content. Best fix?

- A) Disable RAG
- B) Sanitize and tag retrieved content as untrusted
- C) Increase embedding dimensions
- D) Use larger context window

<details>
<summary>Answer</summary>

**B) Sanitize and tag retrieved content as untrusted**

Treat all retrieved content as potentially malicious and apply appropriate filters.

</details>

---

### Q18. You see a spike of 50% blocked requests. What action?

- A) Disable blocking
- B) Investigate attack source and patterns
- C) Increase thresholds automatically
- D) Restart the service

<details>
<summary>Answer</summary>

**B) Investigate attack source and patterns**

A sudden spike indicates possible attack and requires investigation, not disabling defenses.

</details>

---

### Q19. How to protect system prompt from extraction?

- A) Make it longer
- B) Use instruction hierarchy and avoid including secrets
- C) Encrypt the prompt
- D) Use multiple LLMs

<details>
<summary>Answer</summary>

**B) Use instruction hierarchy and avoid including secrets**

Never include secrets in system prompt; enforce instruction hierarchy (system > user).

</details>

---

### Q20. Best practice for API key protection in LLM apps?

- A) Store in system prompt
- B) Use environment variables and secrets manager
- C) Hardcode in source
- D) Pass from client

<details>
<summary>Answer</summary>

**B) Use environment variables and secrets manager**

Never expose API keys to the LLM or client; use proper secrets management.

</details>

---

### Q21. What is "privilege escalation" in LLM agents?

- A) Getting admin access to the server
- B) Agent gaining more capabilities than intended
- C) Increasing API rate limits
- D) Token count increase

<details>
<summary>Answer</summary>

**B) Agent gaining more capabilities than intended**

Attackers can trick agents into accessing tools or data beyond their authorized scope.

</details>

---

### Q22. Which attack targets the RAG retrieval stage?

- A) DAN jailbreak
- B) Embedding poisoning
- C) Prompt stuffing
- D) Temperature manipulation

<details>
<summary>Answer</summary>

**B) Embedding poisoning**

Attackers inject malicious documents designed to be retrieved for specific queries.

</details>

---

### Q23. What is "sandwich attack" in prompt injection?

- A) Wrapping injection between legitimate text
- B) Using multiple prompts
- C) Attacking through API
- D) Memory overflow attack

<details>
<summary>Answer</summary>

**A) Wrapping injection between legitimate text**

The malicious instructions are "sandwiched" between innocent-looking text to evade detection.

</details>

---

### Q24. Which SENTINEL function creates a security pipeline?

- A) `scan()`
- B) `Pipeline()`
- C) `guard()`
- D) `configure()`

<details>
<summary>Answer</summary>

**B) `Pipeline()`**

Pipeline allows chaining multiple engines for multi-stage analysis.

</details>

---

### Q25. What metric tracks security scanner accuracy?

- A) Latency p99
- B) F1 score (precision + recall)
- C) Throughput
- D) Memory usage

<details>
<summary>Answer</summary>

**B) F1 score (precision + recall)**

F1 balances false positives (precision) and false negatives (recall).

</details>

---

### Q26. How do you run SENTINEL in async mode?

- A) `scan_async()`
- B) `await scan()`
- C) `pipeline.analyze_async()`
- D) All of the above

<details>
<summary>Answer</summary>

**C) `pipeline.analyze_async()`**

The pipeline provides async analysis for high-throughput scenarios.

</details>

---

### Q27. What is "canary token" in LLM security?

- A) API key
- B) Decoy data to detect leaks
- C) Rate limit counter
- D) Session ID

<details>
<summary>Answer</summary>

**B) Decoy data to detect leaks**

Canary tokens are unique strings that trigger alerts if they appear in outputs.

</details>

---

### Q28. Which log level is appropriate for blocked threats?

- A) DEBUG
- B) INFO
- C) WARNING
- D) CRITICAL

<details>
<summary>Answer</summary>

**C) WARNING**

Blocked threats should be logged as warnings; successful attacks as critical.

</details>

---

### Q29. What is the recommended scan timeout?

- A) No timeout
- B) 100-500ms
- C) 5-10 seconds
- D) 1 minute

<details>
<summary>Answer</summary>

**B) 100-500ms**

Security scans should be fast enough not to impact user experience significantly.

</details>

---

### Q30. How to handle scan failures?

- A) Block the request
- B) Allow with logging (fail-open) or block (fail-closed)
- C) Retry indefinitely
- D) Ignore errors

<details>
<summary>Answer</summary>

**B) Allow with logging (fail-open) or block (fail-closed)**

Choose based on risk tolerance: fail-open for availability, fail-closed for security.

</details>

---

### Q31. What is "jailbreak persistence"?

- A) Saving jailbreak in database
- B) Jailbreak effects lasting across turns
- C) Permanent model changes
- D) Cached responses

<details>
<summary>Answer</summary>

**B) Jailbreak effects lasting across turns**

Some jailbreaks modify the model's behavior for the entire session.

</details>

---

### Q32. Which attack uses Unicode obfuscation?

- A) SQL injection
- B) Homoglyph attack
- C) Buffer overflow
- D) XSS

<details>
<summary>Answer</summary>

**B) Homoglyph attack**

Using visually similar Unicode characters to bypass pattern matching.

</details>

---

### Q33. What is the role of "system prompt" in security?

- A) User authentication
- B) Establishing model behavior and constraints
- C) API key storage
- D) Logging configuration

<details>
<summary>Answer</summary>

**B) Establishing model behavior and constraints**

System prompts define rules, but should never contain secrets.

</details>

---

### Q34. Which is a sign of Crescendo attack in progress?

- A) Single high-risk request
- B) Gradually increasing risk scores across turns
- C) Rapid request rate
- D) Large payload size

<details>
<summary>Answer</summary>

**B) Gradually increasing risk scores across turns**

Crescendo attacks slowly escalate, evading per-request detection.

</details>

---

### Q35. What does SENTINEL's `is_safe` property indicate?

- A) Request passed all checks
- B) No findings above threshold
- C) Response is encrypted
- D) User is authenticated

<details>
<summary>Answer</summary>

**B) No findings above threshold**

`is_safe` is true when no detected threats exceed configured thresholds.

</details>

---

### Q36. How to secure multi-tenant LLM applications?

- A) Share context between tenants
- B) Isolate data and apply per-tenant policies
- C) Use single global configuration
- D) Disable logging

<details>
<summary>Answer</summary>

**B) Isolate data and apply per-tenant policies**

Tenant isolation prevents cross-tenant data leaks.

</details>

---

### Q37. What is "prompt leaking" via error messages?

- A) LLM crashes
- B) Error messages revealing system prompt contents
- C) API key exposure
- D) Log file corruption

<details>
<summary>Answer</summary>

**B) Error messages revealing system prompt contents**

Verbose errors may inadvertently expose internal configurations.

</details>

---

### Q38. Which OWASP category covers excessive agent permissions?

- A) LLM01 - Prompt Injection
- B) LLM06 - Excessive Agency
- C) LLM09 - Misinformation
- D) LLM10 - Unbounded Consumption

<details>
<summary>Answer</summary>

**B) LLM06 - Excessive Agency**

Excessive Agency addresses overly permissive agent capabilities.

</details>

---

### Q39. What is the purpose of rate limiting in LLM security?

- A) Improve response quality
- B) Prevent resource exhaustion and brute-force attacks
- C) Reduce costs only
- D) Simplify logging

<details>
<summary>Answer</summary>

**B) Prevent resource exhaustion and brute-force attacks**

Rate limiting prevents DoS and slows down automated attack attempts.

</details>

---

### Q40. Best practice for handling PII in prompts?

- A) Store in database
- B) Mask/redact before processing, never log raw
- C) Include in system prompt
- D) Send to external API

<details>
<summary>Answer</summary>

**B) Mask/redact before processing, never log raw**

PII should be protected at all stages to comply with privacy regulations.

</details>

---

## Scoring

| Score | Result |
|-------|--------|
| 75%+ | ✅ PASS - Intermediate Certified |
| 65-74% | ⚠️ Conditional - Review and retry |
| <65% | ❌ FAIL - Complete more training |

---

## Next Steps

After passing:

1. 🎖️ Add "Intermediate Certified" to your profile
2. 📚 Continue to Advanced tracks (06-07)
3. 🧪 Complete STRIKE and Blue Team labs
4. 🏆 Prepare for Advanced Certification

---

*AI Security Academy | Intermediate Certification*
