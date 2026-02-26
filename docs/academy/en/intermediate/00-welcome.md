# Welcome to AI Security Academy

> **Your journey into AI security starts here**

---

## What is AI Security Academy?

AI Security Academy is a comprehensive educational platform designed to teach security professionals, developers, and researchers how to protect AI systems from emerging threats. Whether you're defending against prompt injection attacks, securing agentic AI workflows, or implementing detection systems, this academy provides the knowledge and hands-on skills you need.

---

## Who Is This For?

| Audience | What You'll Learn |
|----------|------------------|
| **Security Engineers** | AI-specific attack vectors, detection techniques, incident response |
| **Developers** | Secure coding practices for LLM applications, defensive patterns |
| **Researchers** | Advanced techniques, mathematical foundations, novel attack discovery |
| **Red Teamers** | Attack methodologies, exploitation techniques, bypass strategies |
| **Blue Teamers** | Detection, monitoring, response procedures |

---

## Academy Structure

The curriculum is organized into progressive modules:

### 🎯 Module 01: Foundations
Build your understanding of AI/ML security fundamentals:
- Neural network architecture and vulnerabilities
- Transformer security model
- Tokenization and embedding spaces
- Training pipeline attack surface

### 🔴 Module 02: Threat Landscape
Master the attack taxonomy:
- OWASP LLM Top 10 (2025)
- OWASP ASI Top 10 (Agentic Systems)
- Model-level attacks (inference, adversarial, extraction)
- Prompt-level attacks (injection, jailbreaking)

### ⚔️ Module 03: Attack Vectors
Deep dive into specific attack techniques:
- Direct and indirect prompt injection
- Jailbreak methodologies (DAN, Crescendo, Many-shot)
- Tool manipulation and privilege escalation
- Multi-turn attack patterns

### 🤖 Module 04: Agentic Security
Secure AI agents and autonomous systems:
- Trust boundaries and isolation
- Agent loop security
- Tool authorization patterns
- Protocol security (MCP, A2A, Function Calling)

### 🛡️ Module 05: Defense Strategies
Build comprehensive defenses:
- System prompt engineering
- Input/output filtering
- Detection patterns (regex, semantic, topological)
- Monitoring and incident response

### 🔬 Module 06: Advanced Topics
Cutting-edge techniques:
- Topological Data Analysis (TDA) for detection
- Red team automation
- Mathematical foundations
- Research frontiers

### 📋 Module 07: Governance
Enterprise security management:
- AI security policies
- Audit frameworks
- Compliance requirements
- Risk assessment

### 🧪 Module 08: Labs
Hands-on practice:
- SENTINEL Blue Team exercises
- STRIKE Red Team challenges
- CTF-style scenarios
- Real-world case studies

---

## Learning Paths

Choose your path based on your role:

### 🔵 Blue Team Path (Defenders)
```
Foundations → Threat Landscape → Defense Strategies → Monitoring → Labs (Blue)
```

### 🔴 Red Team Path (Attackers)
```
Foundations → Attack Vectors → Advanced Topics → Labs (Red)
```

### 🟣 Full Stack Path (Complete Knowledge)
```
All modules in sequence
```

---

## How to Use This Academy

### 1. Prerequisites Check
- Basic understanding of machine learning concepts
- Familiarity with Python programming
- Security fundamentals (helpful but not required)

### 2. Recommended Approach
1. Start with Module 01 regardless of experience level
2. Complete lessons in order within each module
3. Practice with code examples in each lesson
4. Complete lab exercises to reinforce learning

### 3. Lesson Format
Each lesson includes:
- **Learning Objectives** – What you'll be able to do
- **Concept Explanation** – Theory and context
- **Code Examples** – Working Python implementations
- **SENTINEL Integration** – Framework usage patterns
- **Key Takeaways** – Summary for reference

### 4. Time Investment
| Level | Weekly Time | Completion |
|-------|-------------|------------|
| Casual | 2-3 hours | 3-4 months |
| Standard | 5-7 hours | 6-8 weeks |
| Intensive | 15+ hours | 2-3 weeks |

---

## Getting Started

### Quick Start
1. Read the [How to Use This Academy](01-how-to-use.md) guide
2. Begin with [Module 01: ML Fundamentals](../01-ml-fundamentals/)
3. Set up your local SENTINEL environment for labs

### Prerequisites Setup
```bash
# Clone the SENTINEL repository
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m sentinel.verify
```

---

## Community

### Contributing
We welcome contributions! See [Contributing Guide](../contributing.md) for:
- How to submit new lessons
- Style guidelines
- Review process

### Support
- GitHub Issues for bugs and feature requests
- Discussion forums for questions
- Regular office hours (schedule on Discord)

---

## What Makes This Academy Different

| Feature | Traditional Security Training | AI Security Academy |
|---------|------------------------------|---------------------|
| **Focus** | IT/Network security | AI/LLM-specific threats |
| **Attacks Covered** | SQL injection, XSS, etc. | Prompt injection, jailbreaks |
| **Lab Environment** | Virtual networks | Live LLM sandboxes |
| **Defense Tools** | WAF, IDS, SIEM | SENTINEL framework |
| **Updates** | Periodic | Continuous (threat landscape evolves) |

---

## Ready to Begin?

Your AI security journey starts now. The threats are real, the stakes are high, and the knowledge you gain here will be critical as AI systems become more prevalent.

**[Start Module 01: Foundations →](../01-ml-fundamentals/)**

---

*AI Security Academy | Welcome*
