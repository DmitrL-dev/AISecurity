"""
Academy Lesson Linter
Validates formatting, links, and style.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


class LessonLinter:
    """Lint academy lessons for common issues."""

    def __init__(self):
        self.issues: List[Dict] = []

    def lint_file(self, path: Path) -> List[Dict]:
        """Lint a single lesson file."""
        issues = []
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Check 1: Title exists
        if not content.startswith("# "):
            issues.append(
                {
                    "file": str(path),
                    "line": 1,
                    "severity": "error",
                    "message": "Lesson must start with H1 title",
                }
            )

        # Check 2: Broken internal links
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for i, line in enumerate(lines, 1):
            for match in re.finditer(link_pattern, line):
                link_text, link_url = match.groups()

                # Check relative links
                if link_url.startswith("./") or link_url.startswith("../"):
                    link_path = path.parent / link_url
                    if not link_path.exists():
                        issues.append(
                            {
                                "file": str(path),
                                "line": i,
                                "severity": "warning",
                                "message": f"Broken link: {link_url}",
                            }
                        )

        # Check 3: Code blocks closed
        code_opens = (
            content.count("```python")
            + content.count("```json")
            + content.count("```xml")
        )
        code_closes = (
            content.count("```\n") + content.count("```\r\n") + content.count("```")
        )

        # Rough check - should be balanced
        if code_opens > code_closes // 2:
            issues.append(
                {
                    "file": str(path),
                    "line": 0,
                    "severity": "warning",
                    "message": "Potentially unclosed code block",
                }
            )

        # Check 4: TODO/FIXME markers
        for i, line in enumerate(lines, 1):
            if "TODO" in line or "FIXME" in line:
                issues.append(
                    {
                        "file": str(path),
                        "line": i,
                        "severity": "info",
                        "message": f"TODO/FIXME marker found: {line.strip()[:50]}",
                    }
                )

        # Check 5: Excessively long lines
        for i, line in enumerate(lines, 1):
            if len(line) > 200 and not line.startswith("```"):
                issues.append(
                    {
                        "file": str(path),
                        "line": i,
                        "severity": "info",
                        "message": "Line exceeds 200 characters",
                    }
                )

        return issues

    def lint_directory(self, directory: Path) -> List[Dict]:
        """Lint all lessons in directory."""
        all_issues = []

        for path in directory.rglob("*.md"):
            if path.name == "README.md":
                continue

            issues = self.lint_file(path)
            all_issues.extend(issues)

        return all_issues

    def report(self, issues: List[Dict]) -> Tuple[int, int, int]:
        """Print report and return counts."""
        errors = warnings = infos = 0

        for issue in sorted(issues, key=lambda x: (x["file"], x["line"])):
            severity = issue["severity"].upper()
            print(f"[{severity}] {issue['file']}:{issue['line']} - {issue['message']}")

            if issue["severity"] == "error":
                errors += 1
            elif issue["severity"] == "warning":
                warnings += 1
            else:
                infos += 1

        print(f"\nSummary: {errors} errors, {warnings} warnings, {infos} info")
        return errors, warnings, infos


def main():
    """Run linter on academy lessons."""
    linter = LessonLinter()

    academy_path = Path("docs/academy")
    if not academy_path.exists():
        print("Academy directory not found")
        sys.exit(1)

    issues = linter.lint_directory(academy_path)
    errors, warnings, infos = linter.report(issues)

    # Exit with error if any errors found
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
