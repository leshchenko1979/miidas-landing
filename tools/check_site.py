"""Structural checks over the deployed site.

Runs in CI before the artifact is uploaded, so a hand-edit that breaks a link,
duplicates an id or unbalances a tag fails the build instead of reaching
miidas.ru. Complements tools/content_gate.py, which owns copy and encoding.

What it checks, per page:
  * internal links and local asset references resolve to a real file
  * no duplicate id within a page
  * block-level tags balance
  * no U+FFFD replacement characters (a lost character is damage)

Run:  python3 tools/check_site.py [root]
Exit: 0 clean, 1 findings.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

# Build inputs, not pages: the recipe template carries __TOKEN__ placeholders
# that build.sh fills in. It is stripped from the artifact by the workflow.
SKIP = {"recipes/_template.html"}

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

# Tags that are commonly left unclosed in hand-written markup; only these are
# held to the balance rule, so the check cannot fire on someone else's nesting
# style. Anything else is ignored rather than guessed at.
BALANCED = {
    "html", "head", "body", "main", "section", "article", "aside", "nav",
    "header", "footer", "div", "p", "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tr", "td", "th", "a", "span", "strong", "em",
    "button", "form", "label", "figure", "figcaption", "details", "summary",
    "blockquote", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6", "style",
    "script", "title", "caption", "picture", "video", "audio", "select",
    "option", "textarea", "small", "time", "cite", "abbr", "mark", "b", "i",
}

findings: list[str] = []


class Page(HTMLParser):
    """Collect ids, refs and tag balance for one document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.unbalanced: list[tuple[str, int]] = []
        self.ids: list[tuple[str, int]] = []
        self.refs: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if "id" in a and a["id"]:
            self.ids.append((a["id"], line))
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append((a[key], line))
        # Social preview images live in a meta content attribute, not href/src,
        # so a root-absolute URL there is invisible to a link check that only
        # reads links. og:image was broken on every page because of exactly this.
        if tag == "meta" and a.get("property") in ("og:image", "twitter:image"):
            if a.get("content"):
                self.refs.append((a["content"], line))
        if tag in BALANCED and tag not in VOID:
            self.stack.append((tag, line))

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        if "id" in a and a["id"]:
            self.ids.append((a["id"], line))
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append((a[key], line))
        if tag == "meta" and a.get("property") in ("og:image", "twitter:image"):
            if a.get("content"):
                self.refs.append((a["content"], line))

    def handle_endtag(self, tag):
        if tag not in BALANCED:
            return
        line = self.getpos()[0]
        if not self.stack:
            self.unbalanced.append((tag, line))
            return
        # close the nearest matching opener; anything opened after it is unclosed
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for orphan, oline in self.stack[i + 1:]:
                    self.unbalanced.append((orphan, oline))
                del self.stack[i:]
                return
        self.unbalanced.append((tag, line))


SITE_ORIGINS = ("https://miidas.ru", "https://www.miidas.ru")


def targets_for(ref: str, page: Path, root: Path) -> list[Path]:
    """Candidate filesystem targets a reference could resolve to.

    A same-origin absolute URL (https://miidas.ru/x.png) is a real reference to
    a file this repo serves, so it is resolved like a root-absolute path rather
    than skipped as external. Skipping it is how og:image stayed broken on every
    page: the URL looked external to the checker and real to the browser.
    """
    for origin in SITE_ORIGINS:
        if ref.startswith(origin + "/"):
            ref = ref[len(origin):]
            break
    else:
        if ref.startswith(("http://", "https://", "mailto:", "tel:", "data:", "//")):
            return []

    ref = ref.split("#", 1)[0].split("?", 1)[0]
    if not ref:
        return []
    if ref.startswith("/"):
        base = root / ref.lstrip("/")
    else:
        base = page.parent / ref
    base = Path(str(base).replace("%20", " "))
    if ref.endswith("/") or base.is_dir():
        return [base / "index.html", base / "index.htm"]
    return [base]


def check_page(path: Path, root: Path, findings: list[str]) -> None:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")

    if "\ufffd" in text:
        findings.append(f"{rel}: contains U+FFFD replacement characters")

    p = Page()
    p.feed(text)

    for tag, line in p.unbalanced:
        findings.append(f"{rel}:{line}: unbalanced <{tag}>")

    seen: dict[str, int] = {}
    for id_, line in p.ids:
        if id_ in seen:
            findings.append(f"{rel}:{line}: duplicate id #{id_} (first at line {seen[id_]})")
        else:
            seen[id_] = line

    for ref, line in p.refs:
        cands = targets_for(ref, path, root)
        if cands and not any(c.exists() for c in cands):
            findings.append(f"{rel}:{line}: unresolved reference {ref!r}")


def scan(root: Path) -> list[str]:
    """Every finding across the site under `root`."""
    findings: list[str] = []
    pages = sorted(
        p for p in root.rglob("*.html")
        if ".git" not in p.parts and p.relative_to(root).as_posix() not in SKIP
    )
    for page in pages:
        check_page(page, root, findings)
    return findings


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not any(root.rglob("*.html")):
        print(f"check_site: no pages found under {root}", file=sys.stderr)
        return 1

    findings = scan(root)
    pages = len([
        p for p in root.rglob("*.html")
        if ".git" not in p.parts and p.relative_to(root).as_posix() not in SKIP
    ])
    print(f"check_site: {pages} pages scanned, {len(findings)} finding(s)")
    for f in findings:
        print("  " + f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
