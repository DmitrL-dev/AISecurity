# Hands-On Labs

> **Module 08: Practical Exercises**

---

## Overview

Theory without practice is incomplete. This module provides hands-on lab exercises that reinforce concepts from earlier modules. Both blue team (defensive) and red team (offensive) tracks are available.

---

## Lab Tracks

| Track | Focus | Exercises |
|-------|-------|-----------|
| **SENTINEL Blue Team** | Defense, detection, response | 10+ labs |
| **STRIKE Red Team** | Attack, exploitation, evasion | 10+ labs |
| **CTF Challenges** | Competition-style problems | 20+ challenges |

---

## Lab Environment

### Requirements

```bash
# Clone repository
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community

# Install lab dependencies
pip install -r requirements-labs.txt

# Verify setup
python -m labs.verify
```

### Lab Structure

Each lab includes:
- **Objective** - What you'll accomplish
- **Prerequisites** - Required knowledge
- **Instructions** - Step-by-step guide
- **Hints** - If you get stuck
- **Solution** - For verification

---

## Lab Tracks

### [SENTINEL Blue Team](sentinel-blue-team/)
Defensive exercises:
- SENTINEL installation and configuration
- Detection engine tuning
- Alert investigation
- Incident response simulation
- Custom engine development

### [STRIKE Red Team](strike-red-team/)
Offensive exercises:
- Prompt injection crafting
- Jailbreak development
- Defense bypass techniques
- Automated attack generation
- Campaign execution

---

## Difficulty Progression

```
Beginner ──────────────────────────────────────────── Expert

Lab 001        Lab 005        Lab 010        Lab 015
Installation   Basic Detection  Custom Engine   Novel Attack
                                              Development
```

---

## Labs Overview

| Lab ID | Title | Difficulty | Time |
|--------|-------|------------|------|
| 001 | Installation & Setup | Beginner | 30 min |
| 002 | First Scan | Beginner | 20 min |
| 003 | Detection Tuning | Intermediate | 45 min |
| 004 | Alert Investigation | Intermediate | 40 min |
| 005 | Incident Response | Intermediate | 60 min |
| ... | ... | ... | ... |

---

## Completion Tracking

Labs can be completed in any order within a track, but sequential completion is recommended. Track your progress:

```bash
python -m labs.progress --show
```

---

## Getting Help

- **Lab hints** - Available in each lab file
- **Solution files** - For verification (no peeking!)
- **Discussion** - GitHub Discussions for questions
- **Office hours** - Scheduled help sessions

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Governance](../07-governance/) | **Labs** | [Certification](../certification/) |

---

*AI Security Academy | Module 08*
