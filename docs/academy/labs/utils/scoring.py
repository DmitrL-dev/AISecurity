"""
Academy Lab Utils: Scoring System

Scoring and reporting for lab exercises.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class LabScore:
    """Score for a single lab."""

    lab_id: str
    lab_name: str
    exercises: List[Dict[str, Any]] = field(default_factory=list)
    total_points: int = 0
    max_points: int = 0  # Fixed: was 100, should accumulate from exercises

    @property
    def percentage(self) -> float:
        return (self.total_points / self.max_points * 100) if self.max_points else 0

    @property
    def grade(self) -> str:
        p = self.percentage
        if p >= 90:
            return "A"
        if p >= 80:
            return "B"
        if p >= 70:
            return "C"
        if p >= 60:
            return "D"
        return "F"


class LabScorer:
    """
    Score and track progress across labs.

    Usage:
        scorer = LabScorer(student_id="student123")
        scorer.add_exercise("lab-001", "injection", 20, 25)
        scorer.add_exercise("lab-001", "chain", 15, 25)
        report = scorer.generate_report()
    """

    def __init__(self, student_id: str = "anonymous"):
        """Initialize scorer with student ID."""
        self.student_id = student_id
        self.labs: Dict[str, LabScore] = {}
        self.start_time = datetime.now()

    def add_exercise(
        self,
        lab_id: str,
        exercise_name: str,
        points_earned: int,
        max_points: int,
        details: Optional[Dict] = None,
    ):
        """Add exercise result to a lab."""
        if lab_id not in self.labs:
            self.labs[lab_id] = LabScore(
                lab_id=lab_id, lab_name=lab_id.replace("-", " ").title()
            )

        lab = self.labs[lab_id]
        lab.exercises.append(
            {
                "name": exercise_name,
                "earned": points_earned,
                "max": max_points,
                "percentage": (points_earned / max_points * 100) if max_points else 0,
                "details": details or {},
            }
        )
        lab.total_points += points_earned
        lab.max_points += max_points

    def get_lab_score(self, lab_id: str) -> Optional[LabScore]:
        """Get score for specific lab."""
        return self.labs.get(lab_id)

    def get_total_score(self) -> Dict[str, Any]:
        """Get aggregate score across all labs."""
        total_earned = sum(lab.total_points for lab in self.labs.values())
        total_max = sum(lab.max_points for lab in self.labs.values())

        return {
            "student_id": self.student_id,
            "total_points": total_earned,
            "max_points": total_max,
            "percentage": (total_earned / total_max * 100) if total_max else 0,
            "labs_completed": len(self.labs),
            "duration_minutes": (datetime.now() - self.start_time).seconds // 60,
        }

    def generate_report(self) -> str:
        """Generate markdown report."""
        total = self.get_total_score()

        lines = [
            "# Lab Report",
            "",
            f"**Student:** {self.student_id}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Duration:** {total['duration_minutes']} minutes",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"**Total Score:** {total['total_points']}/{total['max_points']} ({total['percentage']:.0f}%)",
            f"**Labs Completed:** {total['labs_completed']}",
            "",
            "---",
            "",
            "## Lab Results",
            "",
        ]

        for lab in self.labs.values():
            lines.append(f"### {lab.lab_name}")
            lines.append("")
            lines.append(
                f"**Score:** {lab.total_points}/{lab.max_points} ({lab.percentage:.0f}%) — Grade: **{lab.grade}**"
            )
            lines.append("")
            lines.append("| Exercise | Earned | Max | % |")
            lines.append("|----------|--------|-----|---|")

            for ex in lab.exercises:
                lines.append(
                    f"| {ex['name']} | {ex['earned']} | {ex['max']} | {ex['percentage']:.0f}% |"
                )

            lines.append("")

        # Certification check
        lines.append("---")
        lines.append("")
        lines.append("## Certification Status")
        lines.append("")

        if total["percentage"] >= 70:
            lines.append("✅ **PASSED** — Eligible for certification")
        else:
            lines.append("❌ **NOT PASSED** — 70% required for certification")

        return "\n".join(lines)

    def export_json(self, path: str):
        """Export results to JSON."""
        data = {
            "student_id": self.student_id,
            "timestamp": datetime.now().isoformat(),
            "total": self.get_total_score(),
            "labs": {
                lab_id: {
                    "name": lab.lab_name,
                    "score": lab.total_points,
                    "max": lab.max_points,
                    "percentage": lab.percentage,
                    "grade": lab.grade,
                    "exercises": lab.exercises,
                }
                for lab_id, lab in self.labs.items()
            },
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def save_report(self, path: str):
        """Save markdown report to file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_report())


# =============================================================================
# QUICK SCORING FUNCTIONS
# =============================================================================


def calculate_score(earned: int, max_points: int) -> Dict[str, Any]:
    """Quick score calculation."""
    percentage = (earned / max_points * 100) if max_points else 0

    grades = [
        (90, "A", "Excellent"),
        (80, "B", "Good"),
        (70, "C", "Satisfactory"),
        (60, "D", "Needs Improvement"),
        (0, "F", "Failed"),
    ]

    grade, description = "F", "Failed"
    for threshold, g, desc in grades:
        if percentage >= threshold:
            grade, description = g, desc
            break

    return {
        "earned": earned,
        "max": max_points,
        "percentage": percentage,
        "grade": grade,
        "description": description,
        "passed": percentage >= 70,
    }


def print_score_box(lab_name: str, earned: int, max_points: int):
    """Print formatted score box."""
    score = calculate_score(earned, max_points)

    print("┌" + "─" * 40 + "┐")
    print(f"│ {lab_name:^38} │")
    print("├" + "─" * 40 + "┤")
    print(
        f"│ Score: {earned:>3}/{max_points:<3} ({score['percentage']:>5.1f}%) {' ' * 14}│"
    )
    print(f"│ Grade: {score['grade']}  — {score['description']:<20}     │")
    print("├" + "─" * 40 + "┤")

    status = "✅ PASSED" if score["passed"] else "❌ NOT PASSED"
    print(f"│ {status:^38} │")
    print("└" + "─" * 40 + "┘")


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("SCORING SYSTEM DEMO")
    print("=" * 50)

    scorer = LabScorer(student_id="demo_student")

    # Add some exercise results
    scorer.add_exercise("lab-001", "path_traversal", 18, 20)
    scorer.add_exercise("lab-001", "tool_chain", 22, 25)
    scorer.add_exercise("lab-001", "privilege_escalation", 15, 20)
    scorer.add_exercise("lab-001", "multi_agent", 18, 20)
    scorer.add_exercise("lab-001", "indirect_injection", 12, 15)

    scorer.add_exercise("lab-002", "roleplay", 20, 25)
    scorer.add_exercise("lab-002", "encoding", 15, 20)
    scorer.add_exercise("lab-002", "delimiter", 18, 20)
    scorer.add_exercise("lab-002", "multi_turn", 16, 20)
    scorer.add_exercise("lab-002", "combined", 12, 15)

    # Print individual lab scores
    for lab_id in scorer.labs:
        lab = scorer.get_lab_score(lab_id)
        print(
            f"\n{lab.lab_name}: {lab.total_points}/{lab.max_points} ({lab.percentage:.0f}%)"
        )

    # Print score box
    total = scorer.get_total_score()
    print()
    print_score_box("TOTAL LABS", total["total_points"], total["max_points"])

    # Generate report
    print("\n" + "=" * 50)
    print("MARKDOWN REPORT")
    print("=" * 50)
    print(scorer.generate_report())
