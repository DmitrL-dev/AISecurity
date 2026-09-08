"""Dependency-free contracts for the repository's public entry surfaces."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class PublicEntryTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.page = Page(self.source)
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.css = (ROOT / "docs/assets/landing.css").read_text(encoding="utf-8")

    def test_spectorn_is_in_the_repository_header(self):
        header = self.readme.split("![", 1)[0]
        self.assertIn("https://spectorn.ai/", header)
        self.assertIn("Spectorn", header)

    def test_entry_paths_and_region_selector_are_real_links(self):
        hrefs = {a["href"] for tag, a in self.page.elements if tag == "a"}
        for required in (
            "https://spectorn.ai/",
            "https://github.com/DmitrL-dev/AISecurity/blob/main/docs/academy/en/index.md",
            "https://github.com/DmitrL-dev/AISecurity/blob/main/docs/academy/ru/index.md",
            "https://github.com/DmitrL-dev/AISecurity/tree/main/tools/guard-lab#install-linux-x86-64--python-311",
        ):
            self.assertIn(required, hrefs)
        self.assertTrue(all(href and href != "#" for href in hrefs))

    def test_local_assets_and_anchors_resolve(self):
        ids = [a["id"] for _, a in self.page.elements if "id" in a]
        self.assertEqual(len(ids), len(set(ids)), "duplicate IDs")
        for tag, attrs in self.page.elements:
            for key in ("href", "src"):
                value = attrs.get(key)
                if not value:
                    continue
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc:
                    self.assertEqual(parsed.scheme, "https")
                elif parsed.path:
                    target = (ROOT / "docs" / parsed.path).resolve()
                    self.assertTrue(target.is_relative_to(ROOT / "docs"))
                    self.assertTrue(target.is_file(), value)
                elif parsed.fragment:
                    self.assertIn(parsed.fragment, ids)

    def test_accessible_structure_and_image_dimensions(self):
        tags = [tag for tag, _ in self.page.elements]
        self.assertEqual(tags.count("h1"), 1)
        self.assertEqual(tags.count("main"), 1)
        self.assertIn("nav", tags)
        self.assertIn("details", tags)
        self.assertIn("summary", tags)
        for tag, attrs in self.page.elements:
            if tag == "img":
                self.assertIn("alt", attrs)
                self.assertGreater(int(attrs["width"]), 0)
                self.assertGreater(int(attrs["height"]), 0)
        self.assertIn(":focus-visible", self.css)

    def test_animation_has_pause_and_reduced_motion(self):
        inputs = [a for tag, a in self.page.elements if tag == "input"]
        labels = [a for tag, a in self.page.elements if tag == "label"]
        self.assertIn({"type": "checkbox", "id": "pause-motion"}, inputs)
        self.assertTrue(any(a.get("for") == "pause-motion" for a in labels))
        self.assertIn("prefers-reduced-motion: reduce", self.css)
        self.assertIn("animation: none", self.css)
        self.assertIn("#pause-motion:checked", self.css)
        self.assertIn("animation-play-state: paused", self.css)
        self.assertIn("Illustrative flow, not a live scan.", self.source)

    def test_no_scripts_tracking_forms_or_external_dependencies(self):
        for tag, attrs in self.page.elements:
            self.assertNotIn(tag, {"script", "iframe", "form", "object", "embed"})
            self.assertFalse(any(key.startswith("on") for key in attrs))
            if tag in {"link", "img"} and attrs.get("rel") != "canonical":
                value = attrs.get("src", attrs.get("href", ""))
                self.assertFalse(urlsplit(value).scheme, value)
        self.assertNotIn("@import", self.css)

    def test_media_budget(self):
        assets = [ROOT / "docs/images/aisecurity-hero.webp",
                  ROOT / "docs/images/aisecurity-banner.webp"]
        for asset in assets:
            self.assertGreater(asset.stat().st_size, 10_000)
            self.assertLess(asset.stat().st_size, 450_000)
        self.assertLess(sum(p.stat().st_size for p in assets), 650_000)

    def test_marketing_keeps_scope_explicit(self):
        for text in (self.source, self.readme):
            self.assertNotRegex(text, r"98\.5%|100%|61 Rust|39K\+")
            self.assertIn("historical", text)
            self.assertIn("not current Spectorn engines", text)
        self.assertIn("synthetic", self.readme)
        self.assertIn("not a benchmark", self.readme)
        self.assertIn("Linux", self.readme)
        self.assertIn("Python 3.11", self.readme)

    def test_readme_relative_links_resolve(self):
        paths = set(re.findall(r"\]\(([^\s)]+)\)", self.readme))
        tracked = set(__import__("subprocess").check_output(
            ["git", "ls-files"], cwd=ROOT, text=True).splitlines())
        for path in paths:
            parsed = urlsplit(path)
            if parsed.scheme or not parsed.path:
                continue
            clean = parsed.path.removeprefix("./").rstrip("/")
            exists = (ROOT / clean).exists()
            tracked_dir = any(p == clean or p.startswith(clean + "/") for p in tracked)
            self.assertTrue(exists or tracked_dir, path)


if __name__ == "__main__":
    unittest.main()
