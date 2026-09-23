#!/usr/bin/env python3
"""Content gate — the rejected-words control the recipes strategy assumed existed.

`recipes-library-strategy-2026-08-22.md` states: "Banned-words gate from the
landing P-language rules applies unchanged". No such gate existed anywhere in
this repo, so persona drift had no mechanical control at all. This is it.

Two rule families, both from project documents rather than taste:

  persona  — the primary persona's explicit "What They DON'T Want" list
             (`docs/persona-primary.md`). The words are rejected because they
             read as IT work, not because they are wrong.
  claim    — promises of full autonomy or of replacing staff. The product keeps
             a human in the loop by design, so these are unsupportable copy
             (`docs/products/factory-lease.md`, and the strategy's section 10).

A deliberate use carries an inline marker on the same line or the line directly
above it, with the reason:

    <!-- content-gate-ok: disqualifier, names the case where it does not apply -->

The marker lives at the copy, so a reviewer sees the justification where it
matters and a line that changes takes its marker with it. There is no file-level
exemption on purpose: an exemption keyed on anything but the matched text drifts
free of what it was written for.

Usage:
    python3 tools/content_gate.py                   # every *.html in the repo
    python3 tools/content_gate.py path [path ...]   # explicit files or dirs

Exit codes: 0 clean, 1 findings, 2 usage error.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import NamedTuple

MARKER = "content-gate-ok"

# A replacement character is always damage, never a stylistic choice, so this
# rule carries no marker exemption. Measured 2026-09-23: two Cyrillic letters on
# the homepage had been lost this way, one of them inside the meta description —
# the string search engines display.
REPLACEMENT = "\ufffd"

PERSONA_TERMS = (
    "интеграц",
    "автоматизац",
    "автоматизир",
    "ии-бухгалтер",
    "ai-бухгалтер",
)

CLAIM_TERMS = (
    "полностью автономн",
    "100% автономн",
    "без участия человека",
    "полностью без участия",
    "заменит бухгалтер",
    "заменит сотрудник",
    "вместо бухгалтера",
)

RULES = {
    "persona": (
        PERSONA_TERMS,
        "primary persona rejects this word family (docs/persona-primary.md)",
    ),
    "claim": (
        CLAIM_TERMS,
        "unsupportable claim: the product keeps a human in the loop",
    ),
}

_TAG = re.compile(r"<[^>]*>")
_WS = re.compile(r"\s+")


class Finding(NamedTuple):
    path: str
    line: int
    rule: str
    term: str
    snippet: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] «{self.term}» — {self.snippet}"


class SourceLine(NamedTuple):
    number: int
    visible: str
    marker: str | None


def _marker_of(raw: str) -> str | None:
    """Return the reason text if this raw line carries a gate marker."""
    idx = raw.lower().find(MARKER)
    if idx < 0:
        return None
    tail = raw[idx + len(MARKER) :]
    return tail.lstrip(" :-—").strip(" ->") or "(no reason given)"


def _scan_html(text: str) -> list[SourceLine]:
    """Per-line visible text, with script, style and comment bodies removed."""
    out: list[SourceLine] = []
    in_script = in_style = in_comment = False
    for number, raw in enumerate(text.splitlines(), start=1):
        marker = _marker_of(raw)
        line = raw
        if in_comment:
            end = line.find("-->")
            if end < 0:
                out.append(SourceLine(number, "", marker))
                continue
            in_comment = False
            line = line[end + 3 :]
        line = re.sub(r"<!--.*?-->", " ", line)
        if "<!--" in line:
            line = line.split("<!--", 1)[0]
            in_comment = True
        lowered = line.lower()
        if in_script:
            in_script = "</script" not in lowered
            out.append(SourceLine(number, "", marker))
            continue
        if in_style:
            in_style = "</style" not in lowered
            out.append(SourceLine(number, "", marker))
            continue
        if "<script" in lowered:
            in_script = "</script" not in lowered
            out.append(SourceLine(number, "", marker))
            continue
        if "<style" in lowered:
            in_style = "</style" not in lowered
            out.append(SourceLine(number, "", marker))
            continue
        out.append(SourceLine(number, html.unescape(_TAG.sub(" ", line)), marker))
    return out


def _scan_markdown(text: str) -> list[SourceLine]:
    """Per-line text with fenced code blocks removed."""
    out: list[SourceLine] = []
    in_fence = False
    for number, raw in enumerate(text.splitlines(), start=1):
        marker = _marker_of(raw)
        if raw.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(SourceLine(number, "", marker))
            continue
        out.append(SourceLine(number, "" if in_fence else raw, marker))
    return out


def scan_text(path: str, text: str) -> list[Finding]:
    """Findings for one file's text. Pure: no filesystem access."""
    lines = _scan_markdown(text) if path.endswith(".md") else _scan_html(text)
    findings: list[Finding] = []
    if REPLACEMENT in text:
        for number, raw in enumerate(text.splitlines(), start=1):
            if REPLACEMENT in raw:
                findings.append(
                    Finding(path, number, "encoding", REPLACEMENT, _WS.sub(" ", raw).strip()[:90])
                )
    for idx, src in enumerate(lines):
        haystack = src.visible.lower()
        if not haystack.strip():
            continue
        excused = src.marker or (lines[idx - 1].marker if idx else None)
        if excused:
            continue
        for rule, (terms, _) in RULES.items():
            for term in terms:
                at = haystack.find(term)
                if at < 0:
                    continue
                window = _WS.sub(" ", src.visible).strip()
                snippet = window[max(0, at - 30) : max(0, at - 30) + 90]
                findings.append(Finding(path, src.number, rule, term, snippet))
    return findings


def iter_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.html")))
        elif path.is_file():
            files.append(path)
        else:
            print(f"content_gate: no such path: {target}", file=sys.stderr)
            raise SystemExit(2)
    return [p for p in files if ".git" not in p.parts]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rejected-words gate for published copy.")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="files or directories to scan (default: every *.html under the repo root)",
    )
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    for path in iter_files(args.paths):
        findings.extend(scan_text(str(path), path.read_text(encoding="utf-8", errors="replace")))

    if not findings:
        print("content_gate: clean")
        return 0
    for finding in findings:
        print(finding)
    print(f"\ncontent_gate: {len(findings)} finding(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
