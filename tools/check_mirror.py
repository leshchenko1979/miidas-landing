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

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_kanal  # noqa: E402
import kanal_posts as kp  # noqa: E402

MARKER = 'class="rz-section kanal-post"'

# Telegram's message limit. The pinned post is a message, so a directory that
# outgrows this cannot be published at all — §4 requires it to stay compact
# enough to scan, and this is the hard ceiling behind that.
TELEGRAM_LIMIT = 4096

SITE_PREFIX = "https://miidas.ru/"
CHANNEL_POST_PREFIX = "https://t.me/miidas_ops/"


def pin_links() -> list[str]:
    """Every url the pinned directory cites."""
    return [u for _, items in kp.PIN["groups"] for _, u in items]


def site_target(url: str) -> Path | None:
    """The file a miidas.ru url would serve, or None when the url is foreign.

    Resolved against the repository this tool ships in, not against `root`:
    the directory cites the live site, and the site's pages are here. A test
    root holds a rendered mirror only, so resolving against it would report
    every site link broken.
    """
    if not url.startswith(SITE_PREFIX):
        return None
    rest = url[len(SITE_PREFIX):].strip("/")
    return ROOT / "index.html" if not rest else ROOT / rest / "index.html"


def check_directory() -> list[str]:
    """The pinned directory against the channel data.

    Guards the failure measured 2026-09-28: three posts published and were
    mirrored on the web while the channel's own map still listed only the
    original three. Both surfaces looked healthy — nothing compared the map to
    what the channel had actually published.
    """
    findings: list[str] = []
    cited = set(pin_links())
    max_id = max(p["id"] for p in kp.POSTS)

    for post in kp.POSTS:
        if post["url"] not in cited:
            findings.append(
                f"kanal_posts.PIN: post {post['id']} is not in the pinned directory "
                f"(the channel's map does not cite {post['url']})"
            )

    for url in sorted(cited):
        if url.startswith(CHANNEL_POST_PREFIX):
            # A link above the newest mirrored post points at something the
            # channel has not published. A link to an id that never existed
            # below that ceiling is not visible here -- stated, not implied.
            tail = url[len(CHANNEL_POST_PREFIX):]
            if not tail.isdigit() or int(tail) > max_id:
                findings.append(
                    f"kanal_posts.PIN: {url} does not resolve — the newest "
                    f"mirrored post is {max_id}"
                )
        else:
            target = site_target(url)
            if target is not None and not target.exists():
                findings.append(
                    f"kanal_posts.PIN: {url} has no page in the repository "
                    f"(expected {target.relative_to(ROOT)})"
                )

    pin_text = build_kanal.render_pin_text()
    for post in kp.POSTS:
        if f"({post['url']})" not in pin_text:
            findings.append(
                f"kanal_posts.PIN: the generated pinned post does not cite "
                f"post {post['id']} ({post['url']})"
            )
    if len(pin_text) > TELEGRAM_LIMIT:
        findings.append(
            f"kanal_posts.PIN: the generated pinned post is {len(pin_text)} "
            f"characters, over Telegram's {TELEGRAM_LIMIT} limit"
        )

    return findings


def has_permalink(html: str, url: str) -> bool:
    """True when `url` sits in the page as a whole token.

    A bare `url in html` is fooled by a longer id that shares the prefix:
    `https://t.me/miidas_ops/9999` contains `https://t.me/miidas_ops/9`, so the
    containment test reports the mirror intact while the real permalink is gone.
    Measured 2026-09-28: inserting post 9 as the newest entry made POSTS[0] an id
    whose prefix matched the control test's sentinel, and the deploy went red --
    the per-post check had been passing on a replaced permalink all along.
    """
    return re.search(re.escape(url) + r"(?![\w/])", html) is not None

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
        if not has_permalink(html, post["url"]):
            findings.append(
                f"kanal/index.html: post {post['id']} is not mirrored "
                f"(missing permalink {post['url']})"
            )
        # The heading, not a bare substring. The directory block cites post
        # titles as link labels, and a label may carry the title as a prefix
        # ("Ошибся бы так же человек? Четыре класса сбоев" contains "Ошибся бы
        # так же человек?"), so a containment test reports the post present
        # while its own row is gone. Measured 2026-09-28 when the directory
        # gained the post links and this check silently stopped being able to
        # fail. The post row is what must carry the title.
        if f"<h3>{post['title']}</h3>" not in html:
            findings.append(
                f"kanal/index.html: post {post['id']} title missing from its row "
                f"(expected <h3>{post['title']}</h3>)"
            )

    rendered = html.count(MARKER)
    if rendered != len(kp.POSTS):
        findings.append(
            f"kanal/index.html: renders {rendered} post(s), "
            f"the data holds {len(kp.POSTS)}"
        )

    if kp.CHANNEL["url"] not in html:
        findings.append("kanal/index.html: no subscribe link to the channel")

    findings.extend(check_directory())

    return findings


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT).resolve()
    findings = check(root)
    print(
        f"check_mirror: {len(kp.POSTS)} post(s) in data, "
        f"channel read at {kp.CHANNEL['fetched_at']}, "
        f"{len(pin_links())} directory link(s), {len(findings)} finding(s)"
    )
    for f in findings:
        print("  " + f)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
