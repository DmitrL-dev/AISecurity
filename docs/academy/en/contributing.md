# Contributing to AI Security Academy

> **Help us build the definitive AI security education platform**

---

## Overview

AI Security Academy is a community-driven project. We welcome contributions from security researchers, developers, educators, and practitioners who want to share their knowledge and improve AI security education worldwide.

---

## Ways to Contribute

### 1. Create New Lessons

We need content across all modules:

| Module | Priority Areas |
|--------|---------------|
| **01-Fundamentals** | New model architectures, multimodal security |
| **02-Threats** | Emerging attack patterns, new OWASP updates |
| **03-Attacks** | Novel techniques, real-world case studies |
| **04-Agentic** | New protocols, framework-specific guides |
| **05-Defense** | Detection improvements, new guardrail patterns |
| **06-Advanced** | Research implementations, mathematical foundations |
| **08-Labs** | Hands-on exercises, CTF challenges |

### 2. Improve Existing Content

- Fix technical errors or outdated information
- Add code examples or clarifications
- Improve diagrams and visualizations
- Update for new framework versions

### 3. Translations

Help make the academy accessible:
- Translate lessons to other languages
- Review existing translations
- Adapt examples for regional contexts

### 4. Lab Exercises

Create practical learning experiences:
- Blue team detection challenges
- Red team attack scenarios
- CTF-style problems
- Real-world simulations

---

## Lesson Structure

All lessons should follow this template:

```markdown
# Lesson Title

> **Lesson:** XX.Y.Z - Short Name  
> **Time:** NN minutes  
> **Prerequisites:** List required prior lessons

---

## Learning Objectives

By the end of this lesson, you will be able to:

1. First measurable objective
2. Second measurable objective
3. Third measurable objective
4. Fourth measurable objective

---

## Main Content

### Section 1: Concept Introduction

Theory and explanation...

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data     | Data     | Data     |

### Section 2: Implementation

```python
class ExampleImplementation:
    """Docstring explaining the class."""
    
    def __init__(self):
        self.attribute = "value"
    
    def method(self, param: str) -> dict:
        """Method docstring."""
        return {"result": param}
```

### Section 3: Advanced Usage

More complex examples...

---

## SENTINEL Integration

```python
from sentinel import configure, Guard

configure(relevant_options=True)

guard = Guard(options=True)

@guard.protect
def example_usage():
    pass
```

---

## Key Takeaways

1. First key point
2. Second key point
3. Third key point
4. Fourth key point
5. Fifth key point

---

*AI Security Academy | Lesson XX.Y.Z*
```

---

## Code Standards

### Python Style

```python
# Use type hints
def function_name(param: str, count: int = 10) -> dict:
    """Docstring with description.
    
    Args:
        param: Description of param
        count: Description of count
        
    Returns:
        Description of return value
    """
    pass

# Use dataclasses for data structures
from dataclasses import dataclass

@dataclass
class ConfigObject:
    name: str
    value: int
    enabled: bool = True

# Use meaningful variable names
attack_pattern = r"ignore.*instructions"  # Good
ap = r"ignore.*instructions"              # Bad

# Include comments for non-obvious logic
# Check for homoglyph attacks by normalizing unicode
normalized = unicodedata.normalize('NFKC', text)
```

### Code Block Requirements

- Always specify language for syntax highlighting
- Include docstrings for classes and complex functions
- Add inline comments for security-relevant logic
- Ensure code is runnable (tested before submission)

---

## Content Guidelines

### Writing Style

- **Clear and direct** - Avoid jargon without explanation
- **Active voice** - "The detector scans for patterns" not "Patterns are scanned for"
- **Practical focus** - Theory supports hands-on application
- **Security mindset** - Think like attacker AND defender

### Technical Accuracy

- All code must be tested and working
- Attack descriptions must be technically sound
- Defense recommendations must be practical
- Keep up with rapidly evolving threat landscape

### Accessibility

- Define acronyms on first use
- Provide context for advanced concepts
- Include diagrams where helpful
- Link to prerequisite content

---

## Submission Process

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR-USERNAME/AISecurity.git
cd AISecurity/sentinel-community
```

### 2. Create Branch

```bash
# Use descriptive branch names
git checkout -b lesson/04-agentic-mcp-security
git checkout -b fix/03-injection-typo
git checkout -b improve/05-detection-examples
```

### 3. Write Content

- Follow the lesson template
- Test all code examples
- Include all required sections
- Keep lessons 200-350 lines

### 4. Self-Review

Check before submitting:
- [ ] Follows lesson template
- [ ] All code runs without errors
- [ ] Learning objectives are measurable
- [ ] Key takeaways summarize main points
- [ ] No spelling/grammar errors
- [ ] Links to other content work

### 5. Submit Pull Request

```bash
git add .
git commit -m "Add lesson: MCP Protocol Security"
git push origin lesson/04-agentic-mcp-security
```

Then open a Pull Request on GitHub with:
- Clear title describing the change
- Summary of what's added/changed
- Any relevant context

---

## Review Process

### What We Check

1. **Technical accuracy** - Is the content correct?
2. **Code quality** - Does it run and follow standards?
3. **Completeness** - Are all sections included?
4. **Clarity** - Is it understandable to the target audience?
5. **Consistency** - Does it match academy style?

### Timeline

- Initial review: 3-5 business days
- Revision requests: Respond within 2 weeks
- Final approval: After all feedback addressed

---

## Recognition

Contributors are recognized:
- Listed in CONTRIBUTORS.md
- Credited in lesson footer
- Featured in release notes
- Invited to contributor community

---

## Questions?

- **Content questions**: Open GitHub Discussion
- **Technical issues**: Open GitHub Issue
- **Process questions**: Email maintainers

---

## Code of Conduct

All contributors must follow our Code of Conduct:
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional standards

---

*Thank you for helping make AI systems more secure!*

---

*AI Security Academy | Contributing Guide*
