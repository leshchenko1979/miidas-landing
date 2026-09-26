#!/usr/bin/env python3
"""Tests for tools/check_mirror.py — the /kanal/ drift gate.

The gate's whole value is that it fails when the mirror falls behind the
channel data. So every case here is a control: break the condition, require
the finding. A check that has never been seen to fail is not a check.

Run:  python3 tests/test_check_mirror.py
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_kanal  # noqa: E402
import check_mirror  # noqa: E402
import kanal_posts as kp  # noqa: E402

# Declared case floor: main() fails when fewer are collected, so a duplicated
# or silently-skipped body cannot report success.
MIN_CASES = 8


class MirrorCase(unittest.TestCase):
    """A throwaway tree holding a freshly rendered mirror."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.page = self.root / "kanal" / "index.html"
        self.page.parent.mkdir(parents=True, exist_ok=True)
        self.page.write_text(build_kanal.build(), encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def findings(self) -> list[str]:
        return check_mirror.check(self.root)

    def mutate(self, old: str, new: str) -> None:
        src = self.page.read_text(encoding="utf-8")
        self.assertIn(old, src, "fixture does not contain the string to mutate")
        self.page.write_text(src.replace(old, new, 1), encoding="utf-8")

    def mutate_all(self, old: str, new: str) -> None:
        """Replace every occurrence — needed when the string also sits in
        site chrome, where replacing one copy leaves the condition intact."""
        src = self.page.read_text(encoding="utf-8")
        self.assertIn(old, src, "fixture does not contain the string to mutate")
        self.page.write_text(src.replace(old, new), encoding="utf-8")


class TestPasses(MirrorCase):
    def test_a_freshly_rendered_mirror_is_clean(self) -> None:
        self.assertEqual(self.findings(), [])


class TestControls(MirrorCase):
    def test_missing_page_is_reported(self) -> None:
        self.page.unlink()
        self.assertTrue(any("missing" in f for f in self.findings()))

    def test_unmirrored_post_is_reported(self) -> None:
        """The real failure: a post exists in the data but not on the page."""
        victim = kp.POSTS[0]
        self.mutate(victim["url"], "https://t.me/miidas_ops/9999")
        found = self.findings()
        self.assertTrue(any("not mirrored" in f for f in found), found)

    def test_dropped_post_row_is_reported(self) -> None:
        """A whole <article> removed, permalink gone with it."""
        victim = kp.POSTS[0]
        src = self.page.read_text(encoding="utf-8")
        start = src.index(f'id="post-{victim["id"]}"')
        start = src.rindex("<article", 0, start)
        end = src.index("</article>", start) + len("</article>")
        self.page.write_text(src[:start] + src[end:], encoding="utf-8")
        found = self.findings()
        self.assertTrue(any("renders" in f or "not mirrored" in f for f in found), found)

    def test_hand_edit_that_drifts_from_the_generator_is_reported(self) -> None:
        self.mutate("<h1>", "<h1>Правка руками ")
        self.assertTrue(any("rerun it" in f for f in self.findings()))

    def test_missing_subscribe_link_is_reported(self) -> None:
        self.mutate_all(kp.CHANNEL["url"], "https://t.me/example")
        self.assertTrue(any("subscribe" in f for f in self.findings()))

    def test_missing_title_is_reported(self) -> None:
        victim = kp.POSTS[0]
        self.mutate(f"<h3>{victim['title']}</h3>", "<h3>Другое</h3>")
        found = self.findings()
        self.assertTrue(any("title missing" in f for f in found), found)


class TestCollection(unittest.TestCase):
    def test_the_suite_itself_is_not_vacuous(self) -> None:
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
        print("check_mirror gate clean: the mirror matches the channel data")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
