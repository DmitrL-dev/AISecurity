# Introduction to AI Security Academy

> **Module 00: Getting Started**

---

## Overview

Welcome to the AI Security Academy. This introductory module will orient you to the curriculum, help you set up your learning environment, and guide you toward the learning path that best fits your goals.

---

## What You'll Learn

This module covers:

| Topic | Description |
|-------|-------------|
| **Academy Structure** | How the curriculum is organized |
| **Learning Paths** | Blue team, red team, and full stack tracks |
| **Environment Setup** | Installing SENTINEL and lab dependencies |
| **Study Strategies** | How to get the most from each lesson |

---

## Lessons in This Module

### [00. Welcome](00-welcome.md)
**Time:** 20 minutes | **Prerequisites:** None

An introduction to the academy, including:
- Who this course is designed for
- What topics are covered
- How modules build on each other
- Community and contribution information

### [01. How to Use This Academy](01-how-to-use.md)
**Time:** 15 minutes | **Prerequisites:** None

Practical guidance on:
- Directory structure and navigation
- Lesson types and formats
- Setting up your development environment
- Tracking your progress

---

## Before You Begin

### Prerequisites

No prior AI security knowledge is required, but you should have:

- **Programming experience** - Comfortable reading/writing Python
- **Basic ML concepts** - Understand what neural networks do (high level)
- **Security mindset** - Curious about how systems can be attacked/defended

### Environment Setup

Quick start for your learning environment:

```bash
# Clone the repository
git clone https://github.com/DmitrL-dev/AISecurity.git
cd AISecurity/sentinel-community
cd sentinel-community

# Create virtual environment
python -m venv ai-security-env
source ai-security-env/bin/activate  # Linux/Mac
# or
.\ai-security-env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Verify
python -c "from sentinel import configure; print('Ready!')"
```

---

## Learning Paths

Choose based on your goals:

### 🔵 Blue Team (Defenders)
Focus on detection, monitoring, and response.
```
00-Introduction → 01-Fundamentals → 02-Threats → 05-Defense → 08-Labs
```

### 🔴 Red Team (Attackers)
Focus on attack techniques and exploitation.
```
00-Introduction → 01-Fundamentals → 03-Attacks → 06-Advanced → 08-Labs
```

### 🟣 Full Stack (Comprehensive)
Complete curriculum for full AI security expertise.
```
All modules in sequence (00 → 08)
```

---

## Navigation

| Module | Focus | Time |
|--------|-------|------|
| [01 - AI Fundamentals](../01-ai-fundamentals/) | ML/AI basics | ~8 hours |
| [02 - Threat Landscape](../02-threat-landscape/) | Attack taxonomy | ~6 hours |
| [03 - Attack Vectors](../03-attack-vectors/) | Specific techniques | ~10 hours |
| [04 - Agentic Security](../04-agentic-security/) | Agent protection | ~8 hours |
| [05 - Defense Strategies](../05-defense-strategies/) | Building defenses | ~10 hours |
| [06 - Advanced](../06-advanced/) | Expert topics | ~6 hours |
| [07 - Governance](../07-governance/) | Policy & compliance | ~4 hours |
| [08 - Labs](../08-labs/) | Hands-on practice | ~12 hours |

---

## Ready to Start?

**[Begin with Welcome →](00-welcome.md)**

---

*AI Security Academy | Module 00*
