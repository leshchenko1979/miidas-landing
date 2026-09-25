#!/usr/bin/env python3
"""Tests for tools/check_site.py — the structural / link gate.

The gate exists because a hand-edit can break a reference without touching a
word of copy, and the content gate cannot see it. It has to catch four classes,
and the fourth is the one it originally missed: og:image lives in a meta
content attribute, not href/src, so a checker that only read links reported the
whole site clean while every social share of miidas.ru showed no preview image.

Run:  python3 tests/test_check_site.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import check_site  # noqa: E402

# The number of cases this file declares. main() fails when the suite loads
# fewer, so a duplicated or silently-skipped body cannot report success.
MIN_CASES = 10

PAGE_HEAD = "<!doctype html><html><head><title>t</title></head><body>"


class SiteCase(unittest.TestCase):
    """Builds a throwaway site tree per case."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def page(self, rel: str, body: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(PAGE_HEAD + body + "</body></html>", encoding="utf-8")
        return p

    def findings(self) -> list[str]:
        return check_site.scan(self.root)


class TestReferences(SiteCase):
    def test_broken_root_absolute_src_is_reported(self) -> None:
        self.page("index.html", '<img src="/missing.jpg">')
        self.assertTrue(any("missing.jpg" in f for f in self.findings()))

    def test_existing_root_absolute_src_passes(self) -> None:
        (self.root / "ok.jpg").write_bytes(b"x")
        self.page("index.html", '<img src="/ok.jpg">')
        self.assertEqual(self.findings(), [])

    def test_directory_reference_resolves_to_index(self) -> None:
        self.page("sub/index.html", "<p>hi</p>")
        self.page("index.html", '<a href="/sub/">go</a>')
        self.assertEqual(self.findings(), [])

    def test_same_origin_og_image_is_resolved_not_skipped(self) -> None:
        """The regression that let the defect through: an absolute URL on our
        own host is a real reference, and must be checked like a local path."""
        self.page("index.html",
                  '<meta property="og:image" content="https://miidas.ru/og-image.png">')
        self.assertTrue(any("og-image.png" in f for f in self.findings()),
                        "same-origin og:image must be resolved, not skipped")

    def test_same_origin_og_image_passes_when_present(self) -> None:
        (self.root / "static").mkdir()
        (self.root / "static" / "og-image.png").write_bytes(b"x")
        self.page("index.html",
                  '<meta property="og:image" content="https://miidas.ru/static/og-image.png">')
        self.assertEqual(self.findings(), [])

    def test_foreign_og_image_is_not_reported(self) -> None:
        """Another host is not ours to resolve."""
        self.page("index.html",
                  '<meta property="og:image" content="https://example.com/x.png">')
        self.assertEqual(self.findings(), [])


class TestStructure(SiteCase):
    def test_duplicate_id_is_reported(self) -> None:
        self.page("index.html", '<div id="a"></div><div id="a"></div>')
        self.assertTrue(any("duplicate id" in f for f in self.findings()))

    def test_unbalanced_tag_is_reported(self) -> None:
        self.page("index.html", "<div><p>unclosed</div>")
        self.assertTrue(any("unbalanced" in f for f in self.findings()))

    def test_replacement_character_is_reported(self) -> None:
        self.page("index.html", "<p>санитар\ufffd\ufffdя</p>")
        self.assertTrue(any("U+FFFD" in f for f in self.findings()))


class TestCollection(unittest.TestCase):
    def test_the_suite_itself_is_not_vacuous(self) -> None:
        """The case floor must bind under pytest as well as via main()."""
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        collected = suite.countTestCases()
        self.assertGreaterEqual(
            collected, MIN_CASES,
            "the suite collected %d cases; it must collect at least %d"
            % (collected, MIN_CASES),
        )


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.testsRun < MIN_CASES:
        print(f"VACUOUS: ran {result.testsRun} cases, expected at least {MIN_CASES}")
        return 1
    if result.wasSuccessful():
        print("check_site gate clean: references resolve, structure intact")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
