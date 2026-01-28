"""
TDD Tests for Academy 2026 Gaps Coverage
Tests run BEFORE implementation to define expected behavior.
"""

import pytest
import os
from pathlib import Path

# Base paths
ACADEMY_EN = Path("docs/academy/en")
ACADEMY_RU = Path("docs/academy/ru")
ACADEMY_LABS = Path("docs/academy/labs")


class TestLessonStructure:
    """Validates that each lesson has required sections."""

    REQUIRED_SECTIONS = [
        "# ",  # Title (H1)
        "## Обзор",  # Overview (or English variant)
        "## Теория",  # Theory
        "## Практика",  # Practice
    ]

    REQUIRED_SECTIONS_EN = [
        "# ",
        "## Overview",
        "## Theory",
        "## Practice",
    ]

    def check_lesson_structure(self, filepath: Path, lang: str = "ru"):
        """Check if lesson has all required sections."""
        if not filepath.exists():
            pytest.skip(f"Lesson not yet created: {filepath}")

        content = filepath.read_text(encoding="utf-8")
        sections = self.REQUIRED_SECTIONS if lang == "ru" else self.REQUIRED_SECTIONS_EN

        missing = []
        for section in sections:
            if section not in content:
                missing.append(section)

        assert not missing, f"Missing sections in {filepath}: {missing}"


class TestPolicyPuppetryLesson(TestLessonStructure):
    """TDD: Policy Puppetry Jailbreak lesson must exist and be complete."""

    def test_en_lesson_exists(self):
        path = ACADEMY_EN / "03-attack-vectors/02-jailbreaks/18-policy-puppetry.md"
        assert path.exists(), f"EN lesson missing: {path}"

    def test_ru_lesson_exists(self):
        path = ACADEMY_RU / "03-attack-vectors/02-jailbreaks/18-policy-puppetry.md"
        assert path.exists(), f"RU lesson missing: {path}"

    def test_en_has_required_sections(self):
        path = ACADEMY_EN / "03-attack-vectors/02-jailbreaks/18-policy-puppetry.md"
        self.check_lesson_structure(path, lang="en")

    def test_contains_gemini_reference(self):
        path = ACADEMY_EN / "03-attack-vectors/02-jailbreaks/18-policy-puppetry.md"
        if not path.exists():
            pytest.skip("Lesson not yet created")
        content = path.read_text(encoding="utf-8")
        assert "Gemini" in content, "Must reference Gemini as primary target"

    def test_contains_code_example(self):
        path = ACADEMY_EN / "03-attack-vectors/02-jailbreaks/18-policy-puppetry.md"
        if not path.exists():
            pytest.skip("Lesson not yet created")
        content = path.read_text(encoding="utf-8")
        assert "```" in content, "Must contain code examples"


class TestConstrainedDecodingLesson(TestLessonStructure):
    """TDD: Constrained Decoding Attack lesson."""

    def test_en_lesson_exists(self):
        path = ACADEMY_EN / "03-attack-vectors/02-jailbreaks/19-constrained-decoding.md"
        assert path.exists(), f"EN lesson missing: {path}"

    def test_ru_lesson_exists(self):
        path = ACADEMY_RU / "03-attack-vectors/02-jailbreaks/19-constrained-decoding.md"
        assert path.exists(), f"RU lesson missing: {path}"

    def test_contains_success_rate(self):
        path = ACADEMY_EN / "03-attack-vectors/02-jailbreaks/19-constrained-decoding.md"
        if not path.exists():
            pytest.skip("Lesson not yet created")
        content = path.read_text(encoding="utf-8")
        assert "96" in content, "Must mention 96.2% success rate"


class TestMCPSecurityLesson(TestLessonStructure):
    """TDD: MCP Security Threats lesson."""

    def test_en_lesson_exists(self):
        path = (
            ACADEMY_EN
            / "03-attack-vectors/01-agentic-attacks/08-mcp-security-threats.md"
        )
        assert path.exists(), f"EN lesson missing: {path}"

    def test_contains_shadow_escape(self):
        path = (
            ACADEMY_EN
            / "03-attack-vectors/01-agentic-attacks/08-mcp-security-threats.md"
        )
        if not path.exists():
            pytest.skip("Lesson not yet created")
        content = path.read_text(encoding="utf-8")
        assert (
            "Shadow Escape" in content or "shadow escape" in content.lower()
        ), "Must describe Shadow Escape exploit"

    def test_contains_tpa(self):
        path = (
            ACADEMY_EN
            / "03-attack-vectors/01-agentic-attacks/08-mcp-security-threats.md"
        )
        if not path.exists():
            pytest.skip("Lesson not yet created")
        content = path.read_text(encoding="utf-8")
        assert (
            "Tool Poisoning" in content or "TPA" in content
        ), "Must describe Tool Poisoning Attacks"


class TestInvisiblePromptsLesson(TestLessonStructure):
    """TDD: Invisible Prompts lesson."""

    def test_en_lesson_exists(self):
        path = (
            ACADEMY_EN / "03-attack-vectors/01-prompt-injection/04-invisible-prompts.md"
        )
        assert path.exists(), f"EN lesson missing: {path}"

    def test_contains_zero_width(self):
        path = (
            ACADEMY_EN / "03-attack-vectors/01-prompt-injection/04-invisible-prompts.md"
        )
        if not path.exists():
            pytest.skip("Lesson not yet created")
        content = path.read_text(encoding="utf-8")
        assert (
            "zero-width" in content.lower() or "U+200B" in content
        ), "Must describe zero-width characters"


class TestInvisiblePromptsLab:
    """TDD: Invisible Prompts Lab."""

    def test_lab_readme_exists(self):
        path = ACADEMY_LABS / "09-invisible-prompts/README.md"
        assert path.exists(), f"Lab README missing: {path}"

    def test_lab_challenge_exists(self):
        path = ACADEMY_LABS / "09-invisible-prompts/challenge.py"
        assert path.exists(), f"Lab challenge missing: {path}"

    def test_lab_has_payloads(self):
        path = ACADEMY_LABS / "09-invisible-prompts/payloads"
        assert path.exists() and path.is_dir(), f"Payloads directory missing: {path}"


class TestBilingualParity:
    """Ensures EN and RU lessons are in sync."""

    NEW_LESSONS = [
        "03-attack-vectors/02-jailbreaks/18-policy-puppetry.md",
        "03-attack-vectors/02-jailbreaks/19-constrained-decoding.md",
        "03-attack-vectors/01-agentic-attacks/08-mcp-security-threats.md",
        "03-attack-vectors/01-prompt-injection/04-invisible-prompts.md",
    ]

    @pytest.mark.parametrize("lesson_path", NEW_LESSONS)
    def test_en_ru_both_exist(self, lesson_path):
        en_path = ACADEMY_EN / lesson_path
        ru_path = ACADEMY_RU / lesson_path

        if not en_path.exists():
            pytest.skip(f"EN lesson not yet created: {lesson_path}")

        assert ru_path.exists(), f"RU version missing for: {lesson_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
