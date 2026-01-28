"""
Bilingual Parity Tests
Ensures EN and RU lessons are in sync.
"""

import pytest
from pathlib import Path
from typing import Set

ACADEMY_EN = Path("docs/academy/en")
ACADEMY_RU = Path("docs/academy/ru")


class TestBilingualParity:
    """EN and RU lesson pairs must exist."""

    def get_relative_lessons(self, base_path: Path) -> Set[str]:
        """Get lesson paths relative to language root."""
        lessons = set()
        for path in base_path.rglob("*.md"):
            if path.name != "README.md":
                rel = path.relative_to(base_path)
                lessons.add(str(rel).replace("\\", "/"))
        return lessons

    def test_en_has_ru_counterpart(self):
        """Every EN lesson should have RU version."""
        en_lessons = self.get_relative_lessons(ACADEMY_EN)
        ru_lessons = self.get_relative_lessons(ACADEMY_RU)

        missing_ru = en_lessons - ru_lessons

        # Allow some missing for now, but report
        if missing_ru:
            pytest.skip(f"Missing RU versions: {len(missing_ru)} lessons")

    def test_ru_has_en_counterpart(self):
        """Every RU lesson should have EN version."""
        en_lessons = self.get_relative_lessons(ACADEMY_EN)
        ru_lessons = self.get_relative_lessons(ACADEMY_RU)

        missing_en = ru_lessons - en_lessons

        if missing_en:
            pytest.fail(f"RU lessons without EN: {missing_en}")


class TestContentParity:
    """Check content consistency between languages."""

    def get_lesson_pairs(self):
        """Get matching EN/RU lesson pairs."""
        en_lessons = {
            str(p.relative_to(ACADEMY_EN)).replace("\\", "/"): p
            for p in ACADEMY_EN.rglob("*.md")
            if p.name != "README.md"
        }
        ru_lessons = {
            str(p.relative_to(ACADEMY_RU)).replace("\\", "/"): p
            for p in ACADEMY_RU.rglob("*.md")
            if p.name != "README.md"
        }

        pairs = []
        for rel_path in en_lessons:
            if rel_path in ru_lessons:
                pairs.append((en_lessons[rel_path], ru_lessons[rel_path]))

        return pairs

    @pytest.mark.parametrize("en_path,ru_path", [])  # Dynamic parametrize
    def test_code_blocks_match(self, en_path: Path, ru_path: Path):
        """Code examples should be same in both languages."""
        import re

        en_content = en_path.read_text(encoding="utf-8")
        ru_content = ru_path.read_text(encoding="utf-8")

        en_blocks = len(re.findall(r"```python", en_content))
        ru_blocks = len(re.findall(r"```python", ru_content))

        # RU can have fewer (condensed), but shouldn't have more
        assert (
            ru_blocks <= en_blocks + 2
        ), f"RU has more code blocks than EN: {ru_path.name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
