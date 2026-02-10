"""C³ Crystal analysis methods for RLMServer.

Extracted from server.py to reduce God Class size.
Contains: _keyword_search, _analyze_summarize, _analyze_find_bugs,
          _analyze_security, _analyze_explain.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class AnalyzersMixin:
    """Analysis helper methods for RLMServer."""

    def _keyword_search(
        self, content: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Simple keyword search for MVP."""
        lines = content.split("\n")
        query_words = set(query.lower().split())
        scored = []

        for i, line in enumerate(lines):
            line_lower = line.lower()
            score = sum(1 for w in query_words if w in line_lower)
            if score > 0:
                scored.append((score, i, line.strip()))

        scored.sort(reverse=True)
        chunks = []
        for score, line_num, line_content in scored[:top_k]:
            chunks.append(
                {
                    "content": line_content,
                    "line": line_num + 1,
                    "score": score,
                }
            )

        return chunks

    def _analyze_summarize(self, crystal: Any) -> Dict[str, Any]:
        """Generate a summary of the code structure."""
        primitives = crystal.primitives
        classes = [p for p in primitives if p.type.value == "class"]
        functions = [p for p in primitives if p.type.value == "function"]
        return {
            "summary": (
                f"File contains {len(classes)} classes "
                f"and {len(functions)} functions"
            ),
            "classes": [p.name for p in classes],
            "functions": [p.name for p in functions[:20]],
            "total_primitives": len(primitives),
        }

    def _analyze_find_bugs(self, crystal: Any) -> Dict[str, Any]:
        """Find potential bugs and code smells."""
        issues = []
        for p in crystal.primitives:
            if p.content:
                # Long function
                lines = p.content.count("\n")
                if lines > 50:
                    issues.append(
                        {
                            "type": "code_smell",
                            "name": p.name,
                            "issue": (f"Long function " f"({lines} lines)"),
                            "severity": "warning",
                        }
                    )

                # Bare except
                if "except:" in p.content:
                    issues.append(
                        {
                            "type": "bug_risk",
                            "name": p.name,
                            "issue": ("Bare except clause " "catches all exceptions"),
                            "severity": "error",
                        }
                    )

                # TODO/FIXME
                for marker in ["TODO", "FIXME", "HACK"]:
                    if marker in p.content:
                        match = re.search(
                            rf"{marker}[:\s]*(.*?)(?:\n|$)",
                            p.content,
                        )
                        if match:
                            issues.append(
                                {
                                    "type": "todo",
                                    "name": p.name,
                                    "issue": (match.group(0).strip()),
                                    "severity": "info",
                                }
                            )

                # No docstring
                if (
                    p.type.value == "function"
                    and '"""' not in p.content[:100]
                    and "'''" not in p.content[:100]
                ):
                    issues.append(
                        {
                            "type": "code_smell",
                            "name": p.name,
                            "issue": "Missing docstring",
                            "severity": "info",
                        }
                    )

        return {
            "total_issues": len(issues),
            "errors": [i for i in issues if i["severity"] == "error"],
            "warnings": [i for i in issues if i["severity"] == "warning"],
            "info": [i for i in issues if i["severity"] == "info"],
        }

    def _analyze_security(self, crystal: Any) -> Dict[str, Any]:
        """Security audit of the code."""
        findings = []
        security_patterns = {
            "eval(": "Dangerous eval() usage",
            "exec(": "Dangerous exec() usage",
            "subprocess": "Subprocess execution",
            "os.system": "OS command execution",
            "__import__": "Dynamic import",
            "pickle.loads": "Unsafe deserialization",
            "yaml.load(": ("Unsafe YAML loading " "(use safe_load)"),
            "shell=True": ("Shell injection risk"),
            "password": "Potential hardcoded secret",
            "api_key": "Potential API key exposure",
            "secret": "Potential secret exposure",
        }

        for p in crystal.primitives:
            if p.content:
                content_lower = p.content.lower()
                for pattern, desc in security_patterns.items():
                    if pattern.lower() in content_lower:
                        findings.append(
                            {
                                "pattern": pattern,
                                "description": desc,
                                "location": p.name,
                                "severity": (
                                    "critical"
                                    if pattern
                                    in [
                                        "eval(",
                                        "exec(",
                                        "pickle.loads",
                                    ]
                                    else "warning"
                                ),
                            }
                        )

        return {
            "total_findings": len(findings),
            "critical": [f for f in findings if f["severity"] == "critical"],
            "warnings": [f for f in findings if f["severity"] == "warning"],
        }

    def _analyze_explain(self, crystal: Any) -> Dict[str, Any]:
        """Explain the code structure."""
        primitives = crystal.primitives
        explanation = []

        for p in primitives:
            doc = ""
            if p.content and '"""' in p.content:
                match = re.search(
                    r'"""(.*?)"""',
                    p.content,
                    re.DOTALL,
                )
                if match:
                    doc = match.group(1).strip()[:200]

            explanation.append(
                {
                    "name": p.name,
                    "type": p.type.value,
                    "docstring": doc or "No documentation",
                    "line_start": p.start_line,
                }
            )

        return {
            "total_items": len(explanation),
            "items": explanation[:30],
        }
