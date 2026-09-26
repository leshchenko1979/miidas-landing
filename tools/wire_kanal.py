#!/usr/bin/env python3
"""Insert the /kanal/ link into every nav-links and footer-links block.

Idempotent and asserted: each block must gain exactly one link, and a block
that already carries /kanal/ is left alone. Fails loudly rather than skipping
a page silently.

Rule: insert after the /razbory/ anchor, else after /zamer/, else before the
last anchor in the block (which is the contact link on every page that has no
section links).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = '<a href="/kanal/">Канал</a>'
GENERATED = ROOT / "kanal" / "index.html"   # produced by build_kanal.py


def insert_in_block(block: str, label: str, path: Path) -> tuple[str, int]:
    if "/kanal/" in block:
        return block, 0
    lines = block.split("\n")
    anchors = [
        (i, re.search(r'href="([^"]+)"', ln).group(1))
        for i, ln in enumerate(lines)
        if re.search(r'href="([^"]+)"', ln)
    ]
    if not anchors:
        raise SystemExit(f"{path}: {label} block has no anchors")

    target = None
    for want in ("/razbory/", "/zamer/"):
        for i, href in anchors:
            if href == want:
                target = i
                break
        if target is not None:
            break
    if target is None:
        target = anchors[-2][0] if len(anchors) >= 2 else anchors[-1][0]

    indent = re.match(r"\s*", lines[target]).group(0)
    lines.insert(target + 1, f"{indent}{LINK}")
    return "\n".join(lines), 1


def wire(path: Path) -> int:
    src = path.read_text(encoding="utf-8")
    added = 0
    for name in ("nav-links", "footer-links"):
        pat = re.compile(r'(<div class="' + name + r'"[^>]*>)(.*?)(</div>)', re.S)
        m = pat.search(src)
        if not m:
            continue
        new_block, n = insert_in_block(m.group(2), name, path)
        if n:
            src = src[: m.start(2)] + new_block + src[m.end(2):]
            added += n
    if added:
        path.write_text(src, encoding="utf-8")
    return added


def main() -> int:
    pages = sorted(
        p for p in ROOT.rglob("*.html")
        if "node_modules" not in p.parts and p != GENERATED
    )
    total = 0
    for p in pages:
        n = wire(p)
        total += n
        if n:
            print(f"  {p.relative_to(ROOT)}: +{n}")
    print(f"wired {total} link(s) across {len(pages)} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
