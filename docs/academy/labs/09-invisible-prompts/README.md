# Lab 09: Invisible Prompts Detection

> **Level:** Intermediate  
> **Time:** 45 minutes  
> **Prerequisites:** Lesson 04 (Invisible Prompts)

---

## Objectives

1. Detect zero-width characters in user input
2. Identify homoglyph attacks (mixed scripts)
3. Build a comprehensive invisible prompt detector
4. Test against real-world payloads

---

## Setup

```bash
cd docs/academy/labs/09-invisible-prompts
python -m pytest challenge.py -v
```

---

## Challenge 1: Zero-Width Detection

Implement `detect_zero_width()` that finds all invisible characters:

```python
def detect_zero_width(text: str) -> dict:
    """
    Find zero-width and invisible Unicode characters.
    
    Returns:
        {
            'found': bool,
            'count': int,
            'positions': [(index, char_code, char_name), ...]
        }
    """
    # YOUR CODE HERE
    pass
```

**Test cases:**
- `"Hello world"` → found: False
- `"Hello\u200Bworld"` → found: True, count: 1
- `"Te\u200Bst\u200C\u200D"` → found: True, count: 3

---

## Challenge 2: Homoglyph Detection

Implement `detect_homoglyphs()` that identifies mixed-script lookalikes:

```python
def detect_homoglyphs(text: str) -> dict:
    """
    Detect Cyrillic/Greek characters disguised as Latin.
    
    Returns:
        {
            'found': bool,
            'mixed_scripts': set of script names,
            'suspicious_chars': [(index, char, script), ...]
        }
    """
    # YOUR CODE HERE
    pass
```

**Test cases:**
- `"normal text"` → found: False
- `"hеllo"` (Cyrillic е) → found: True
- `"pаssword"` (Cyrillic а) → found: True

---

## Challenge 3: Full Detector

Build `InvisiblePromptDetector` class that combines all detection methods:

```python
class InvisiblePromptDetector:
    def analyze(self, text: str) -> dict:
        """
        Complete analysis for invisible prompt attacks.
        
        Returns:
            {
                'is_malicious': bool,
                'risk_score': float (0-1),
                'zero_width': {...},
                'homoglyphs': {...},
                'recommendations': [str, ...]
            }
        """
        # YOUR CODE HERE
        pass
    
    def sanitize(self, text: str) -> str:
        """
        Remove all invisible/suspicious characters.
        Returns clean text.
        """
        # YOUR CODE HERE
        pass
```

---

## Challenge 4: Bypass the Detector

Using payloads in `payloads/` directory, try to bypass your detector:

1. Can you create a payload that passes detection but still works?
2. What edge cases did you find?
3. How would you improve your detector?

---

## Grading

| Challenge | Points | Criteria |
|-----------|--------|----------|
| Challenge 1 | 25 | All test cases pass |
| Challenge 2 | 25 | Mixed script detection works |
| Challenge 3 | 30 | Full detector with sanitization |
| Challenge 4 | 20 | Creative bypass + improvement |

**Total: 100 points**

---

## Hints

<details>
<summary>Hint 1: Zero-Width Characters</summary>

Common zero-width codes:
- U+200B: Zero Width Space
- U+200C: Zero Width Non-Joiner
- U+200D: Zero Width Joiner
- U+FEFF: Byte Order Mark
- U+2060: Word Joiner

</details>

<details>
<summary>Hint 2: Script Detection</summary>

Use `unicodedata.name()` to get character names:
```python
import unicodedata
name = unicodedata.name('а')  # 'CYRILLIC SMALL LETTER A'
```

</details>

<details>
<summary>Hint 3: Sanitization</summary>

NFKC normalization handles many cases:
```python
import unicodedata
clean = unicodedata.normalize('NFKC', text)
```

</details>

---

## Solutions

Solutions are in `solutions/detector.py`. Try to complete the challenges before looking!

---

*Lab 09 — Invisible Prompts Detection*
