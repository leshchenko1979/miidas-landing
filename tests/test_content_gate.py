#!/usr/bin/env python3
"""Tests for tools/content_gate.py — the rejected-words gate.

The gate exists because `recipes-library-strategy-2026-08-22.md` assumed a
"P-language rules" control that did not exist. A gate is only a control if it
has teeth, so these cases assert the three things that make it one:

  1. it fires on the terms the persona actually rejects (every stem, not a sample)
  2. it stays silent on the surfaces that are not buyer-facing copy
  3. it honours a reasoned inline marker, and ONLY when adjacent to the match

Run:  python3 tests/test_content_gate.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import content_gate  # noqa: E402

# The number of cases this file declares. main() fails when the suite loads
# fewer, so a duplicated or silently-skipped body cannot report success.
MIN_CASES = 18


def findings(text: str, path: str = "page.html") -> list:
    return content_gate.scan_text(path, text)


class TestDetection(unittest.TestCase):
    def test_persona_term_is_detected(self):
        self.assertEqual(len(findings("<p>Мы делаем интеграцию с CRM</p>")), 1)

    def test_every_persona_stem_is_detected(self):
        for term in content_gate.PERSONA_TERMS:
            with self.subTest(term=term):
                self.assertTrue(findings(f"<p>текст {term} дальше</p>"), term)

    def test_every_claim_stem_is_detected(self):
        for term in content_gate.CLAIM_TERMS:
            with self.subTest(term=term):
                self.assertTrue(findings(f"<p>работает {term} совсем</p>"), term)

    def test_clean_copy_produces_no_findings(self):
        self.assertEqual(findings("<p>Отдел, который не надо нанимать.</p>"), [])

    def test_finding_carries_line_rule_and_term(self):
        found = findings("<p>ok</p>\n<p>интеграция</p>")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].line, 2)
        self.assertEqual(found[0].rule, "persona")
        self.assertEqual(found[0].term, "интеграц")


class TestExcuse(unittest.TestCase):
    def test_marker_on_the_same_line_excuses(self):
        self.assertEqual(findings("<p>интеграция</p><!-- content-gate-ok: reason -->"), [])

    def test_marker_on_the_line_above_excuses(self):
        text = "<!-- content-gate-ok: reason -->\n<p>интеграция</p>"
        self.assertEqual(findings(text), [])

    def test_marker_two_lines_above_does_not_excuse(self):
        text = "<!-- content-gate-ok: reason -->\n<p>spacer</p>\n<p>интеграция</p>"
        self.assertEqual(len(findings(text)), 1)

    def test_excuse_applies_to_one_line_not_the_file(self):
        text = (
            "<!-- content-gate-ok: reason -->\n"
            "<p>интеграция</p>\n"
            "<p>другая интеграция</p>"
        )
        self.assertEqual(len(findings(text)), 1)


class TestNonCopyIsNotScanned(unittest.TestCase):
    def test_html_comment_body_is_ignored(self):
        self.assertEqual(findings("<p>ok</p><!-- интеграция -->"), [])

    def test_script_body_is_ignored(self):
        self.assertEqual(findings("<script>var s = 'интеграция';</script>"), [])

    def test_style_body_is_ignored(self):
        self.assertEqual(findings("<style>.a { content: 'интеграция' }</style>"), [])

    def test_markdown_fence_is_ignored(self):
        self.assertEqual(findings("## t\n```\nинтеграция\n```\n", path="doc.md"), [])

    def test_tag_split_token_is_not_matched(self):
        self.assertEqual(findings("<p>автомати<strong>зация</strong></p>"), [])


class TestTeeth(unittest.TestCase):
    """Proves the detector depends on its rules, and restores them in a finally."""

    def test_emptying_the_rules_stops_detection_then_restores(self):
        saved = dict(content_gate.RULES)
        try:
            for rule, (_, reason) in saved.items():
                content_gate.RULES[rule] = ((), reason)
            self.assertEqual(findings("<p>интеграция</p>"), [], "detector fired on empty rules")
        finally:
            content_gate.RULES.clear()
            content_gate.RULES.update(saved)
        self.assertEqual(len(findings("<p>интеграция</p>")), 1, "rules not restored")


class TestEncoding(unittest.TestCase):
    """A lost character is damage, and no marker may excuse it."""

    def test_replacement_character_is_reported(self):
        found = findings("<p>под \ufffd\ufffdлюч</p>")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].rule, "encoding")

    def test_replacement_character_cannot_be_excused(self):
        text = "<!-- content-gate-ok: looks deliberate -->\n<p>под \ufffd\ufffdлюч</p>"
        self.assertEqual(len(findings(text)), 1)


class TestPublishedCopy(unittest.TestCase):
    """The regression guard for the live site itself."""

    def test_every_published_page_is_clean(self):
        files = content_gate.iter_files([str(ROOT)])
        self.assertGreaterEqual(len(files), 8, "repo scan found too few pages to be real")
        found = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            found.extend(content_gate.scan_text(str(path), text))
        self.assertEqual(found, [], f"gate findings: {found}")


def run_case_suite() -> bool:
    """Run every declared case. A suite that loads too few is a failure."""
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    count = suite.countTestCases()
    if count < MIN_CASES:
        print(f"FAIL: suite loaded {count} cases, expected at least {MIN_CASES}")
        return False
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    ok = run_case_suite()
    print("OK" if ok else "FAILED")
    raise SystemExit(0 if ok else 1)
