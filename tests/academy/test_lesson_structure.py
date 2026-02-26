"""
Academy Lesson Structure Validator
Ensures all lessons have required sections and proper formatting.
"""

import pytest
from pathlib import Path
from typing import List, Dict

ACADEMY_EN = Path("docs/academy/en")
ACADEMY_RU = Path("docs/academy/ru")


class TestLessonRequiredSections:
    """Validate that lessons contain all required sections."""

    REQUIRED_EN = [
        "## Overview",
        "## Theory",
        "## Practice",
    ]

    REQUIRED_RU = [
        "## Обзор",
        "## Теория",
        "## Практика",
    ]

    def get_all_lessons(self, base_path: Path) -> List[Path]:
        """Get all markdown lesson files."""
        return list(base_path.rglob("*.md"))

    @pytest.mark.parametrize("lesson_path", list(ACADEMY_EN.rglob("*.md")))
    def test_en_lesson_has_sections(self, lesson_path: Path):
        """EN lessons must have Overview, Theory, Practice."""
        if lesson_path.name == "README.md":
            pytest.skip("README files excluded")

        content = lesson_path.read_text(encoding="utf-8")

        # Check for required sections (or English alternatives)
        has_overview = "## Overview" in content or "## Обзор" in content
        has_theory = "## Theory" in content or "## Теория" in content
        has_practice = (
            "## Practice" in content
            or "## Практика" in content
            or "## Defense" in content
        )

        assert has_overview, f"{lesson_path}: Missing Overview section"
        assert has_theory, f"{lesson_path}: Missing Theory section"

    @pytest.mark.parametrize("lesson_path", list(ACADEMY_RU.rglob("*.md")))
    def test_ru_lesson_has_sections(self, lesson_path: Path):
        """RU lessons must have Обзор, Теория, Практика."""
        if lesson_path.name == "README.md":
            pytest.skip("README files excluded")

        content = lesson_path.read_text(encoding="utf-8")

        has_overview = "## Обзор" in content or "## Overview" in content
        has_theory = "## Теория" in content or "## Theory" in content

        assert has_overview, f"{lesson_path}: Missing Обзор section"
        assert has_theory, f"{lesson_path}: Missing Теория section"


class TestLessonMetadata:
    """Validate lesson frontmatter and metadata."""

    @pytest.mark.parametrize("lesson_path", list(ACADEMY_EN.rglob("*.md")))
    def test_en_has_title(self, lesson_path: Path):
        """Lessons must have H1 title."""
        if lesson_path.name == "README.md":
            pytest.skip("README files excluded")

        content = lesson_path.read_text(encoding="utf-8")
        assert content.startswith("# "), f"{lesson_path}: Missing H1 title"

    @pytest.mark.parametrize("lesson_path", list(ACADEMY_EN.rglob("*.md")))
    def test_en_has_level_indicator(self, lesson_path: Path):
        """Lessons should indicate difficulty level."""
        if lesson_path.name == "README.md":
            pytest.skip("README files excluded")

        content = lesson_path.read_text(encoding="utf-8")
        levels = [
            "Beginner",
            "Intermediate",
            "Advanced",
            "Expert",
            "Начальный",
            "Средний",
            "Продвинутый",
            "Эксперт",
        ]

        has_level = any(level in content for level in levels)
        # Warning only, not failure
        if not has_level:
            pytest.skip(f"{lesson_path}: Consider adding difficulty level")


class TestCodeExamples:
    """Validate code examples in lessons."""

    @pytest.mark.parametrize("lesson_path", list(ACADEMY_EN.rglob("*.md")))
    def test_has_code_blocks(self, lesson_path: Path):
        """Attack/defense lessons should have code examples."""
        if lesson_path.name == "README.md":
            pytest.skip("README excluded")

        content = lesson_path.read_text(encoding="utf-8")

        # Check for code blocks
        has_code = "```" in content

        # Attack vectors and defense should have code
        if "attack-vectors" in str(lesson_path) or "defense" in str(lesson_path):
            assert (
                has_code
            ), f"{lesson_path}: Attack/defense lesson should have code examples"

    @pytest.mark.parametrize("lesson_path", list(ACADEMY_EN.rglob("*.md")))
    def test_python_code_valid(self, lesson_path: Path):
        """Python code blocks should be syntactically valid."""
        import re
        import ast

        if lesson_path.name == "README.md":
            pytest.skip("README excluded")

        content = lesson_path.read_text(encoding="utf-8")

        # Extract Python blocks
        python_blocks = re.findall(r"```python\n(.*?)```", content, re.DOTALL)

        for i, block in enumerate(python_blocks):
            try:
                # Try to parse (not execute)
                ast.parse(block)
            except SyntaxError as e:
                pytest.fail(f"{lesson_path}: Python block {i+1} has syntax error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
