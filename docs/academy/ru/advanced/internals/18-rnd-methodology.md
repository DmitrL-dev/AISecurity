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

```rust
fn triage_finding(finding: &Finding) -> &'static str {
    /// Evaluate R&D finding for action.

    let mut score = 0;

    // Impact
    if finding.affects_agents { score += 3; }
    if finding.affects_rag { score += 2; }
    if finding.novel_technique { score += 2; }

    // Urgency
    if finding.has_cve { score += 3; }
    if finding.in_the_wild { score += 3; }

    // Feasibility
    if finding.detection_possible { score += 2; }
    if finding.has_samples { score += 1; }

    // Prioritize
    if score >= 8 {
        "P0 - Immediate action"
    } else if score >= 5 {
        "P1 - This week"
    } else {
        "P2 - Backlog"
    }
}
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

```rust
use reqwest::blocking::Client;

fn scan_arxiv_daily() -> Vec<Paper> {
    /// Scan arXiv for AI security papers.

    let queries = vec![
        "prompt injection",
        "jailbreak LLM",
        "adversarial attack language model",
        "AI agent security",
        "RAG poisoning",
    ];

    let client = Client::new();
    let mut papers = Vec::new();
    for query in &queries {
        let results = arxiv_search(
            &client,
            query,
            10,    // max_results
            SortCriterion::SubmittedDate,
        );
        papers.extend(results);
    }

    // Filter last 7 days
    let recent: Vec<Paper> = papers
        .into_iter()
        .filter(|p| is_recent(&p.published, 7))
        .collect();

    deduplicate(recent)
}
```

---

## CVE Monitoring

```rust
use reqwest::blocking::Client;
use serde_json::Value;

fn check_ai_cves() -> Vec<Value> {
    /// Check for AI-related CVEs.

    let keywords = vec![
        "LLM", "GPT", "Claude", "Gemini",
        "LangChain", "Ollama", "OpenAI",
        "prompt injection", "AI agent",
    ];

    let client = Client::new();
    let mut cves = Vec::new();
    for keyword in &keywords {
        let response: Value = client
            .get("https://services.nvd.nist.gov/rest/json/cves/2.0")
            .query(&[("keywordSearch", keyword)])
            .send()
            .unwrap()
            .json()
            .unwrap();
        if let Some(vulns) = response.get("vulnerabilities") {
            if let Some(arr) = vulns.as_array() {
                cves.extend(arr.clone());
            }
        }
    }

    cves
}
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
