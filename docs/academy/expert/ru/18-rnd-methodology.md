# 📰 Урок 5.1: R&D Methodology

> **Время: 35 минут** | Expert Module 5 — Threat Intelligence

---

## Daily R&D Process

```
Morning Scan → Triage → Analysis → Implementation → Report
   (30 min)    (15 min)  (1-2 hr)     (2-4 hr)      (30 min)
```

---

## Sources

| Priority | Source | Frequency |
|----------|--------|-----------|
| 🔴 P0 | CVE Database | Daily |
| 🔴 P0 | arXiv cs.CR, cs.LG | Daily |
| 🟡 P1 | AI Security blogs | Daily |
| 🟡 P1 | HiddenLayer, Lakera | Weekly |
| 🟢 P2 | Academic conferences | Monthly |
| 🟢 P2 | Industry reports | Quarterly |

---

## Triage Framework

```python
def triage_finding(finding):
    """Evaluate R&D finding for action."""
    
    score = 0
    
    # Impact
    if finding.affects_agents:
        score += 3
    if finding.affects_rag:
        score += 2
    if finding.novel_technique:
        score += 2
    
    # Urgency
    if finding.has_cve:
        score += 3
    if finding.in_the_wild:
        score += 3
    
    # Feasibility
    if finding.detection_possible:
        score += 2
    if finding.has_samples:
        score += 1
    
    # Prioritize
    if score >= 8:
        return "P0 - Immediate action"
    elif score >= 5:
        return "P1 - This week"
    else:
        return "P2 - Backlog"
```

---

## R&D Report Template

```markdown
# R&D Report: [Date]

## Executive Summary
[1-2 sentences on key findings]

## Findings

### Finding 1: [Title]
- **Source:** [URL]
- **Priority:** P0/P1/P2
- **Impact:** [OWASP mapping]
- **Summary:** [2-3 sentences]
- **Action:** [Engine name or "Research needed"]

### Finding 2: ...

## Action Items
- [ ] Item 1 (Owner, Deadline)
- [ ] Item 2

## Statistics
- Sources scanned: X
- Findings: Y
- Actionable: Z
```

---

## arXiv Scanning

```python
import arxiv

def scan_arxiv_daily():
    """Scan arXiv for AI security papers."""
    
    queries = [
        "prompt injection",
        "jailbreak LLM",
        "adversarial attack language model",
        "AI agent security",
        "RAG poisoning",
    ]
    
    papers = []
    for query in queries:
        search = arxiv.Search(
            query=query,
            max_results=10,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        papers.extend(search.results())
    
    # Filter last 7 days
    recent = [p for p in papers if is_recent(p.published, days=7)]
    
    return deduplicate(recent)
```

---

## CVE Monitoring

```python
import requests

def check_ai_cves():
    """Check for AI-related CVEs."""
    
    keywords = [
        "LLM", "GPT", "Claude", "Gemini",
        "LangChain", "Ollama", "OpenAI",
        "prompt injection", "AI agent"
    ]
    
    cves = []
    for keyword in keywords:
        response = requests.get(
            f"https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"keywordSearch": keyword}
        )
        cves.extend(response.json().get("vulnerabilities", []))
    
    return cves
```

---

## Knowledge Integration

```
Finding → Engine → Tests → PR → Release → CDN
                                    ↓
                            signatures/jailbreaks.json
```

---

## Следующий урок

→ [5.2: CVE Analysis](./19-cve-analysis.md)
