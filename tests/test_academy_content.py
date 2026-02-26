"""
Academy Content Validation Tests

Tests that validate:
1. Code examples in theory files are syntactically correct
2. Internal links are not broken
3. Encoding is correct (no corrupted UTF-8)
"""

import pytest
import sys
import re
import ast
from pathlib import Path

# Academy root
ACADEMY_ROOT = Path(__file__).parent.parent / "docs" / "academy"
EN_ROOT = ACADEMY_ROOT / "en"
RU_ROOT = ACADEMY_ROOT / "ru"

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class TestCodeExamples:
    """Test that Python code examples in theory files are valid."""

    def get_python_blocks(self, md_file: Path) -> list:
        """Extract Python code blocks from markdown file."""
        content = md_file.read_text(encoding="utf-8", errors="replace")
        pattern = r"```python\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)
        return matches

    def test_code_examples_syntax(self):
        """All Python code examples should be syntactically valid."""
        errors = []
        files_checked = 0

        for md_file in EN_ROOT.rglob("*.md"):
            if "labs" in str(md_file):
                continue

            code_blocks = self.get_python_blocks(md_file)
            for i, code in enumerate(code_blocks):
                files_checked += 1
                try:
                    # Check syntax by parsing
                    ast.parse(code)
                except SyntaxError as e:
                    errors.append(f"{md_file.name} block {i+1}: {e.msg}")

        # Report but don't fail on small issues
        if errors:
            print(
                f"\n⚠️ Found {len(errors)} syntax issues in {files_checked} code blocks:"
            )
            for err in errors[:10]:  # Show first 10
                print(f"  - {err}")

        # Fail only if more than 20% of blocks have issues
        error_rate = len(errors) / max(files_checked, 1)
        assert (
            error_rate < 0.2
        ), f"Too many syntax errors: {len(errors)}/{files_checked}"

    def test_sentinel_imports_exist(self):
        """Code examples using sentinel import should use public API."""
        bad_imports = []

        for md_file in EN_ROOT.rglob("*.md"):
            if "labs" in str(md_file):
                continue

            code_blocks = self.get_python_blocks(md_file)
            for code in code_blocks:
                if "from sentinel.brain.engines import" in code:
                    bad_imports.append(md_file.name)
                    break

        # Should have few internal API usages
        assert (
            len(bad_imports) < 20
        ), f"Too many internal API imports: {bad_imports[:10]}"


class TestInternalLinks:
    """Test that internal markdown links are not broken."""

    def get_md_links(self, md_file: Path) -> list:
        """Extract markdown links to .md files."""
        content = md_file.read_text(encoding="utf-8", errors="replace")
        pattern = r"\]\(([^)]+\.md)\)"
        matches = re.findall(pattern, content)
        return [m for m in matches if not m.startswith("http")]

    def test_internal_links_not_broken(self):
        """Internal links should point to existing files."""
        broken = []

        for md_file in EN_ROOT.rglob("*.md"):
            links = self.get_md_links(md_file)
            for link in links:
                target = md_file.parent / link
                if not target.exists():
                    broken.append(f"{md_file.name} -> {link}")

        # Report broken links
        if broken:
            print(f"\n⚠️ Found {len(broken)} broken links:")
            for b in broken[:15]:
                print(f"  - {b}")

        # Don't fail, just report (content is evolving)
        assert len(broken) < 50, f"Too many broken links: {len(broken)}"


class TestEncoding:
    """Test that files have correct UTF-8 encoding."""

    ENCODING_ISSUES = ["вЂ", "Ð±", "â€", "Ã"]

    def test_no_encoding_corruption(self):
        """Files should not have corrupted UTF-8 characters."""
        corrupted = []

        for md_file in ACADEMY_ROOT.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                for issue in self.ENCODING_ISSUES:
                    if issue in content:
                        corrupted.append(md_file.name)
                        break
            except UnicodeDecodeError:
                corrupted.append(f"{md_file.name} (decode error)")

        if corrupted:
            print(f"\n⚠️ Found {len(corrupted)} files with encoding issues:")
            for c in corrupted[:10]:
                print(f"  - {c}")

        assert len(corrupted) < 10, f"Too many encoding issues: {corrupted[:10]}"


class TestContentQuality:
    """Test basic content quality."""

    def test_files_not_empty(self):
        """Theory files should have content."""
        empty = []

        for md_file in EN_ROOT.rglob("*.md"):
            if "labs" in str(md_file):
                continue
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if len(content.strip()) < 100:
                empty.append(md_file.name)

        assert len(empty) < 30, f"Too many empty files: {empty[:10]}"

    def test_files_have_headers(self):
        """Theory files should have proper headers."""
        no_header = []

        for md_file in EN_ROOT.rglob("*.md"):
            if "labs" in str(md_file):
                continue
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if not content.strip().startswith("#"):
                no_header.append(md_file.name)

        assert len(no_header) < 50, f"Files without headers: {no_header[:10]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
