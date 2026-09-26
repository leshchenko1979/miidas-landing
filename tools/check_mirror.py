#!/usr/bin/env python3
"""Gate the /kanal/ channel mirror against drift.

CONTENT-FUNNEL.md §2.1 requires every published post to appear on /kanal/
verbatim. The failure this guards is quiet: a post publishes, nobody mirrors
it, and the page keeps looking healthy while falling behind the channel.

What is checkable from CI:
  - the page is exactly what tools/build_kanal.py renders (so a hand-edit
    cannot drift it away from its own data, and a forgotten regeneration fails)
  - every post in the data is on the page, with its live permalink
  - the rendered post count matches the data

What is NOT checkable from CI, and is therefore stated rather than implied:
nothing here reaches Telegram. A post published after kanal_posts.CHANNEL
["fetched_at"] is invisible to this gate — the data file records that instant
so the gap is visible instead of silent.

Usage:  python3 tools/check_mirror.py [root]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_kanal  # noqa: E402
import kanal_posts as kp  # noqa: E402

MARKER = 'class="rz-section kanal-post"'


def check(root: Path) -> list[str]:
    findings: list[str] = []
    page = root / "kanal" / "index.html"

    if not page.exists():
        return [f"kanal/index.html: the channel mirror is missing under {root}"]

    html = page.read_text(encoding="utf-8")

    expected = build_kanal.build()
    if html != expected:
        findings.append(
            "kanal/index.html: not what tools/build_kanal.py renders — "
            "rerun it (a hand-edit, or a post added to the data and never rebuilt)"
        )

    for post in kp.POSTS:
        if post["url"] not in html:
            findings.append(
                f"kanal/index.html: post {post['id']} is not mirrored "
                f"(missing permalink {post['url']})"
            )
        if post["title"] not in html:
            findings.append(
                f"kanal/index.html: post {post['id']} title missing from the page"
            )

    rendered = html.count(MARKER)
    if rendered != len(kp.POSTS):
        findings.append(
            f"kanal/index.html: renders {rendered} post(s), "
            f"the data holds {len(kp.POSTS)}"
        )

    if kp.CHANNEL["url"] not in html:
        findings.append("kanal/index.html: no subscribe link to the channel")

    return findings


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT).resolve()
    findings = check(root)
    print(
        f"check_mirror: {len(kp.POSTS)} post(s) in data, "
        f"channel read at {kp.CHANNEL['fetched_at']}, {len(findings)} finding(s)"
    )
    for f in findings:
        print("  " + f)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
