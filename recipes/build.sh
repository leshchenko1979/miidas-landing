#!/bin/bash
# landing/recipes/build.sh — Render a recipe page from JSON metadata + _template.html
#
# Usage:
#   bash build.sh <content.json> <out_dir>
#
# Example:
#   bash build.sh content/listings.json _test_out/
#
# Produces <out_dir>/<slug>/index.html with all __TOKEN__ placeholders filled in.
#
# JSON schema (content/*.json):
#   slug              — kebab-case ASCII, 1–80 chars (becomes URL path)
#   title             — page title (e.g. "Как автоматизировать объявления для Авито")
#   meta_description  — <meta> description, ≤160 chars recommended
#   og_image          — full URL for og:image (default: https://miidas.ru/static/og-image.png)
#   problem_html      — HTML fragment for § Проблема (plain text, <p>, <ul>, etc.)
#   mockup_html       — HTML fragment for § Что делает бот (Telegram mockup markup)
#   artifact_lead     — one-liner before the code block
#   artifact_text     — the template/code to copy
#   source_audit_ref  — internal ref for analytics (e.g. "avi

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <content.json> <out_dir>" >&2
    exit 64
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/_template.html"
CONTENT_JSON="$1"
OUT_DIR="$2"

if [ ! -f "$TEMPLATE" ]; then
    echo "Template not found: $TEMPLATE" >&2
    exit 66
fi

if [ ! -f "$CONTENT_JSON" ]; then
    echo "Content JSON not found: $CONTENT_JSON" >&2
    exit 66
fi

# ── Parse JSON → env vars (safe for values with newlines/quotes) ──────────
JSON_ENV=$(python3 - "$CONTENT_JSON" <<'PY'
import json, sys, shlex

with open(sys.argv[1], "r", encoding="utf-8") as f:
    d = json.load(f)

required = ["slug", "title", "meta_description", "problem_html", "mockup_html",
            "artifact_lead", "artifact_text", "source_audit_ref"]
missing = [k for k in required if k not in d]
if missing:
    print("ERROR: missing required fields:", ", ".join(missing), file=sys.stderr)
    sys.exit(65)

for k, v in d.items():
    val = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    print(f"export META_{k.upper()}={shlex.quote(val)}")

PY
) || exit 65
eval "$JSON_ENV"

SLUG="${META_SLUG}"
TITLE="${META_TITLE}"
META_DESCRIPTION="${META_META_DESCRIPTION}"
OG_IMAGE="${META_OG_IMAGE:-https://miidas.ru/static/og-image.png}"
PROBLEM_HTML="${META_PROBLEM_HTML}"
MOCKUP_HTML="${META_MOCKUP_HTML}"
ARTIFACT_LEAD="${META_ARTIFACT_LEAD}"
ARTIFACT_TEXT="${META_ARTIFACT_TEXT}"
SOURCE_AUDIT_REF="${META_SOURCE_AUDIT_REF}"

# ── Validate slug ──────────────────────────────────────────────────────────
if ! [[ "$SLUG" =~ ^[a-z0-9][a-z0-9-]{0,80}$ ]]; then
    echo "Invalid slug: '$SLUG' — must be kebab-case ASCII, 1–80 chars" >&2
    exit 65
fi

CANONICAL_URL="https://miidas.ru/recipes/${SLUG}/"

# ── Render template ────────────────────────────────────────────────────────
OUT_PATH="${OUT_DIR%/}/${SLUG}/index.html"
mkdir -p "$(dirname "$OUT_PATH")"

python3 - "$TEMPLATE" "$OUT_PATH" "$SLUG" "$TITLE" "$META_DESCRIPTION" \
          "$CANONICAL_URL" "$OG_IMAGE" "$PROBLEM_HTML" "$MOCKUP_HTML" \
          "$ARTIFACT_LEAD" "$ARTIFACT_TEXT" "$SOURCE_AUDIT_REF" <<'PY'
import sys, re

(template_path, out_path, slug, title, meta_desc, canonical,
 og_image, problem, mockup, lead, artifact, source_ref) = sys.argv[1:13]

with open(template_path, "r", encoding="utf-8") as f:
    tpl = f.read()

replacements = {
    "__CANONICAL_URL__": canonical,
    "__META_DESCRIPTION__": meta_desc,
    "__TITLE__": title,
    "__SLUG__": slug,
    "__OG_IMAGE__": og_image,
    "__PROBLEM_HTML__": problem,
    "__MOCKUP_HTML__": mockup,
    "__ARTIFACT_LEAD__": lead,
    "__ARTIFACT_TEXT__": artifact,
}

for token, value in replacements.items():
    tpl = tpl.replace(token, value)

# Verify every placeholder was consumed
leftover = re.findall(r"__[A-Z_]+__", tpl)
if leftover:
    print("ERROR: leftover placeholders:", sorted(set(leftover)), file=sys.stderr)
    sys.exit(67)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(tpl)

print(f"OK → {out_path}  (source: {source_ref})")
PY
