#!/usr/bin/env python3
"""Render /kanal/ — the web mirror of the Telegram channel.

Source of truth is tools/kanal_posts.py. This script only converts the
channel's own markup to HTML and lays the page out, so the post text on the
site is the post text that was published, not a re-typed copy.

Usage:  python3 tools/build_kanal.py [--check]
        --check  render to memory and report whether kanal/index.html is current
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kanal_posts as kp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "kanal" / "index.html"

CANONICAL = "https://miidas.ru/kanal/"
OG_IMAGE = "https://miidas.ru/static/og-image.png"
TITLE = f"{kp.CHANNEL['title']} — канал и все посты — МИИДАС"
DESC = (
    "Полное содержимое Telegram-канала «Отдел, который не надо нанимать»: "
    "разборы, замеры и границы применимости отдела из агентов. С методом и датами."
)

NAV_LINKS = [
    ("/", "Главная"),
    ("/factory/", "Фабрики агентов"),
    ("/zamer/", "Замеры"),
    ("/kanal/", "Канал"),
    ("/recipes/", "Рецепты"),
    ("/razbory/", "Разборы"),
    ("/course/", "Практикум"),
    ("https://t.me/leshchenko1979", "Связаться"),
]

FOOTER_LINKS = [
    ("/factory/", "Фабрики агентов"),
    ("/zamer/", "Замеры"),
    ("/kanal/", "Канал"),
    ("/agent/", "Аренда агента"),
    ("/course/", "Обучение"),
    ("/recipes/", "Рецепты"),
    ("/razbory/", "Разборы"),
    ("https://t.me/miidas_ops", "Telegram-канал"),
    ("https://t.me/leshchenko1979", "Связаться с основателем"),
]


def inline(text: str) -> str:
    """Channel markup -> HTML. Only the three forms the channel actually uses."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def blocks(body: str) -> list[str]:
    """Split a post body into paragraphs, dropping the leading title line.

    The title is rendered as the heading, so repeating it as the first
    paragraph would print it twice.
    """
    parts = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    if parts and parts[0].startswith("**") and parts[0].endswith("**"):
        parts = parts[1:]
    return parts


def render_nav() -> str:
    links = "\n".join(
        f'            <a href="{href}">{label}</a>' for href, label in NAV_LINKS
    )
    return f"""    <nav class="landing-nav" aria-label="Навигация">
        <a href="/" class="nav-brand">МИИДАС</a>
        <button type="button" class="nav-toggle" aria-label="Открыть меню" aria-expanded="false" aria-controls="nav-links">
            <span></span><span></span><span></span>
        </button>
        <div class="nav-links" id="nav-links">
{links}
        </div>
    </nav>"""


def render_footer() -> str:
    links = "\n".join(
        f'            <a href="{href}">{label}</a>' for href, label in FOOTER_LINKS
    )
    return f"""    <footer>
        <div><strong>МИИДАС</strong> · Экосистема прикладного ИИ для бизнеса · <a href="https://miidas.ru">miidas.ru</a></div>
        <div class="footer-links">
{links}
        </div>
    </footer>"""


def render_directory() -> str:
    """The web equivalent of the pinned navigation post (law §2.1.4)."""
    out = [f'        <p class="rz-index-intro">{inline(kp.PIN["promise"])}</p>']
    out.append('        <div class="kanal-dir">')
    for heading, items in kp.PIN["groups"]:
        out.append(f'            <div class="kanal-dir-group">')
        out.append(f'                <h3>{heading}</h3>')
        out.append("                <ul>")
        for label, url in items:
            out.append(f'                    <li><a href="{url}">{label}</a></li>')
        out.append("                </ul>")
        out.append("            </div>")
    out.append("        </div>")
    return "\n".join(out)


def render_post(post: dict) -> str:
    body = "\n".join(f"                <p>{inline(p)}</p>" for p in blocks(post["body"]))
    deep_href, deep_label = post["deep"]
    return f"""        <article class="rz-section kanal-post" id="post-{post['id']}">
            <p class="kanal-post-meta">
                <time datetime="{post['date']}">{post['date_ru']}</time>
                · <a href="{post['url']}" target="_blank" rel="noopener">Пост в Telegram</a>
            </p>
            <h3>{post['title']}</h3>
{body}
            <p class="kanal-post-deep"><a href="{deep_href}">{deep_label} →</a></p>
        </article>"""


def build() -> str:
    posts = sorted(kp.POSTS, key=lambda p: p["id"], reverse=True)
    rendered = "\n\n".join(render_post(p) for p in posts)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230c0c0c'/%3E%3Ctext x='50%25' y='54%25' text-anchor='middle' font-family='system-ui,sans-serif' font-weight='800' font-size='36' fill='%233db4ff'%3EM%3C/text%3E%3C/svg%3E">

    <title>{TITLE}</title>
    <meta name="description" content="{DESC}">
    <meta property="og:title" content="{TITLE}">
    <meta property="og:description" content="{DESC}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{CANONICAL}">
    <meta property="og:image" content="{OG_IMAGE}">

    <link rel="canonical" href="{CANONICAL}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Onest:wght@500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="../style.css?v=1789518342">
    <link rel="stylesheet" href="../article.css">
    <link rel="stylesheet" href="kanal.css">
</head>
<body>
{render_nav()}

    <main class="rz-page">
        <p class="rz-eyebrow">Telegram-канал</p>
        <h1>{kp.CHANNEL['title']}</h1>

        <p class="rz-lede">{kp.CHANNEL['promise']}</p>

        <div class="rz-subscribe">
            <p>Каждый пост выходит сначала в канале. Здесь лежит его полный текст: удобно перечитать, найти поиском и передать коллеге.</p>
            <div class="rz-tg-row">
                <a class="rz-tg-link" href="{kp.CHANNEL['url']}" target="_blank" rel="noopener">Подписаться на Telegram</a>
            </div>
        </div>

        <h2 class="rz-grid-heading">С чего начать</h2>

{render_directory()}

        <h2 class="rz-grid-heading">Все посты канала</h2>

        <p class="rz-index-intro">
            Ниже — полные тексты постов, от новых к старым, {len(posts)} шт. Дата у каждого поста — дата публикации в канале.
            Там, где у поста есть подробная версия с методом и таблицей, рядом стоит ссылка на неё.
        </p>

{rendered}

        <div class="rz-cta" style="margin-top: 64px;">
            <div class="cta-row">
                <button class="cta-primary cta-clean" type="button" data-source="kanal_index">Попробовать МИИДАС в Telegram</button>
                <a href="https://t.me/leshchenko1979" target="_blank" rel="noopener" class="cta-secondary">Разобрать один процесс с основателем →</a>
            </div>
            <p class="cta-microcopy">14 дней бесплатно, без карты. Никаких автосписаний.</p>
        </div>

        <p id="claimStatus" class="claim-status claim-toast hidden" role="status" aria-live="polite"></p>
    </main>

{render_footer()}

    <script src="../app.js?v=1789518342"></script>
</body>
</html>
"""


def main() -> int:
    html = build()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current == html:
            print("kanal: current")
            return 0
        print("kanal: STALE — rerun tools/build_kanal.py")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"kanal: wrote {OUT.relative_to(ROOT)} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
