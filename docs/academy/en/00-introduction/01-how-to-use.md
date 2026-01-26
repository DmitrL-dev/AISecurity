# How to Use This Academy

> **Lesson:** 00.1 - Academy Navigation Guide  
> **Time:** 15 minutes

---

## Learning Objectives

By the end of this guide, you will be able to:

1. Navigate the academy structure efficiently
2. Set up your learning environment
3. Follow the recommended learning paths
4. Get the most from each lesson type

---

## Academy Structure

### Directory Organization

```
docs/academy/en/
├── 00-introduction/        # Start here
├── 01-ml-fundamentals/     # Core knowledge
├── 02-threat-landscape/    # Attack taxonomy
├── 03-attack-vectors/      # Specific techniques
├── 04-agentic-security/    # Agent protection
├── 05-defense-strategies/  # Defensive measures
├── 06-advanced/            # Expert topics
├── 07-governance/          # Policy & compliance
├── 08-labs/                # Hands-on exercises
└── certification/          # Assessment tracks
```

### Module Numbering

Each module is prefixed with a number indicating recommended order:
- **00-0x**: Introduction and navigation
- **01-0x**: Foundational knowledge
- **02-0x**: Threat understanding
- **03-0x - 05-0x**: Core competencies
- **06-0x+**: Advanced and specialized

---

## Lesson Types

### Theory Lessons
- Concept explanations with diagrams
- Tables summarizing key points
- ~200-350 lines of content
- Estimated time: 30-45 minutes

### Code Lessons
- Python implementations you can run
- SENTINEL framework integration
- Copy-paste ready examples
- Estimated time: 45-60 minutes

### Lab Exercises
- Hands-on challenges
- Scenario-based problems
- Graded difficulty levels
- Estimated time: 60-120 minutes

### Reference Materials
- Quick lookup guides
- Cheat sheets
- Pattern libraries
- Use as needed

---

## Setting Up Your Environment

### Minimum Requirements

```bash
# Python 3.10+
python --version

# Git
git --version

# Recommended: Virtual environment
python -m venv ai-security-env
source ai-security-env/bin/activate  # Linux/Mac
.\ai-security-env\Scripts\activate   # Windows
```

### Installing SENTINEL

```bash
# Clone repository
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Install dependencies
pip install -r requirements.txt

# Install SENTINEL package
pip install -e .

# Verify installation
python -c "from sentinel import configure; print('SENTINEL ready')"
```

### Lab Environment

For practical exercises, you'll need:

```bash
# Additional lab dependencies
pip install -r requirements-labs.txt

# Verify lab setup
python -m labs.verify_setup
```

---

## Learning Paths

### 🔵 Path A: Security Analyst (4 weeks)

Focus on detection, monitoring, and response.

**Week 1: Foundations**
- 01-ml-fundamentals/01-basics/*
- 01-ml-fundamentals/02-architecture/*

**Week 2: Threats**
- 02-threat-landscape/01-owasp-llm-top10/*
- 02-threat-landscape/02-owasp-asi-top10/*

**Week 3: Defense**
- 05-defense-strategies/01-detection/*
- 05-defense-strategies/02-guardrails/*

**Week 4: Operations**
- 05-defense-strategies/03-monitoring/*
- 08-labs/sentinel-blue-team/*

---

### 🔴 Path B: Red Team Specialist (4 weeks)

Focus on attack techniques and exploitation.

**Week 1: Foundations**
- 01-ml-fundamentals/* (all)

**Week 2: Attack Vectors**
- 03-attack-vectors/01-prompt-injection/*
- 03-attack-vectors/02-jailbreaking/*

**Week 3: Advanced Attacks**
- 03-attack-vectors/03-model-level/*
- 04-agentic-security/03-trust/* 

**Week 4: Practice**
- 06-advanced/01-red-teaming/*
- 08-labs/strike-red-team/*

---

### 🟣 Path C: Full Stack AI Security (8 weeks)

Complete curriculum for comprehensive knowledge.

**Weeks 1-2**: Modules 00-02
**Weeks 3-4**: Modules 03-04
**Weeks 5-6**: Modules 05-06
**Weeks 7-8**: Modules 07-08 + Certification

---

## Getting the Most from Lessons

### Before Each Lesson
1. Check prerequisites listed at the top
2. Have your environment ready
3. Review previous lesson's key takeaways

### During Each Lesson
1. Read theory sections carefully
2. Type out code examples (don't just copy-paste)
3. Run all code and observe outputs
4. Take notes on key concepts

### After Each Lesson
1. Complete any exercises
2. Try modifying code examples
3. Review key takeaways
4. Connect concepts to previous lessons

---

## Code Examples

Every lesson includes runnable code. Here's how to use them:

### Inline Examples
```python
# This is a standalone example
from sentinel import configure

configure(
    detection=True,
    logging=True
)

# You can copy and run this directly
```

### Class-Based Examples
```python
class ExampleDetector:
    """Full implementation for learning.
    
    Copy entire class to your project to use.
    """
    
    def __init__(self):
        self.patterns = []
    
    def detect(self, text: str) -> dict:
        # Implementation here
        return {"detected": False}

# Usage
detector = ExampleDetector()
result = detector.detect("test input")
```

### SENTINEL Integration Examples
```python
from sentinel import configure, Guard

# These examples show real framework usage
# They require SENTINEL to be installed

configure(
    feature_flag=True,
    another_option="value"
)

guard = Guard(
    options_here=True
)

@guard.protect
def my_function():
    pass
```

---

## Progress Tracking

### Self-Assessment
After each module, test yourself:
- Can you explain the key concepts?
- Can you reproduce the code from memory?
- Can you apply these techniques to new scenarios?

### Certification
Complete the certification track to validate knowledge:
- Written assessment (concepts)
- Practical assessment (labs)
- Scenario-based challenges

---

## Getting Help

### Documentation
- Each lesson is self-contained
- READMEs provide module overviews
- Search within the docs directory

### Community
- GitHub Discussions for questions
- Issue tracker for bugs
- Contributing guide for improvements

### Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Verify SENTINEL installation |
| Lab failures | Check `requirements-labs.txt` |
| Missing examples | Pull latest from repository |

---

## Next Steps

You're ready to begin! Start with:

**[Module 01: ML Fundamentals →](../01-ml-fundamentals/)**

---

*AI Security Academy | How to Use Guide*
