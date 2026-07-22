#!/usr/bin/env python3
"""Build blog posts from Word (.docx) files using Pandoc.

For every ``posts/*.docx`` file this script:
  1. Reads an optional sidecar ``posts/<name>.meta.yaml`` (title, date, tags,
     description). Missing fields fall back to sensible defaults.
  2. Computes reading time from the document word count.
  3. Renders a styled HTML post at ``blog/<slug>.html`` via Pandoc, reusing
     ``templates/post-template.html`` so posts match the portfolio design.
  4. Regenerates ``blog/index.html`` — a listing page of all posts.

Requires: pandoc (system) and PyYAML (pip).
"""

from __future__ import annotations

import datetime as _dt
import html
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
BLOG_DIR = ROOT / "blog"
TEMPLATE = ROOT / "templates" / "post-template.html"
WORDS_PER_MINUTE = 200


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "post"


def title_from_filename(path: pathlib.Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def load_meta(docx: pathlib.Path) -> dict:
    """Load optional sidecar metadata, applying defaults."""
    meta: dict = {}
    sidecar = docx.with_suffix(".meta.yaml")
    if sidecar.exists():
        loaded = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            meta.update(loaded)

    meta.setdefault("title", title_from_filename(docx))
    meta.setdefault("date", _dt.date.today().isoformat())

    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    meta["tags"] = tags
    return meta


def word_count(docx: pathlib.Path) -> int:
    """Approximate word count by converting the docx to plain text."""
    result = subprocess.run(
        ["pandoc", str(docx), "--from", "docx", "--to", "plain"],
        capture_output=True,
        text=True,
        check=True,
    )
    return len(result.stdout.split())


def render_post(docx: pathlib.Path, slug: str, meta: dict, reading_time: int) -> None:
    media_dir = BLOG_DIR / "assets" / slug
    metadata = {
        "title": meta["title"],
        "date": meta["date"],
        "tags": meta["tags"],
        "reading-time": reading_time,
    }
    if meta.get("description"):
        metadata["description"] = meta["description"]

    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.safe_dump(metadata, fh, allow_unicode=True)
        meta_file = fh.name

    subprocess.run(
        [
            "pandoc",
            str(docx),
            "--from", "docx",
            "--to", "html5",
            "--standalone",
            "--template", str(TEMPLATE),
            "--metadata-file", meta_file,
            "--extract-media", str(media_dir),
            "--toc",
            "--toc-depth", "3",
            "--highlight-style", "breezedark",
            "-o", str(BLOG_DIR / f"{slug}.html"),
        ],
        check=True,
    )
    pathlib.Path(meta_file).unlink(missing_ok=True)


def render_index(posts: list[dict]) -> None:
    posts.sort(key=lambda p: p["date"], reverse=True)
    cards = []
    for post in posts:
        tags = "".join(
            f'<span class="tag">{html.escape(t)}</span>' for t in post["tags"]
        )
        desc = (
            f'<p class="post-desc">{html.escape(post["description"])}</p>'
            if post.get("description")
            else ""
        )
        cards.append(
            f'''      <a class="post-card" href="{post['slug']}.html">
        <h2>{html.escape(post['title'])}</h2>
        <div class="post-meta">
          <span>{html.escape(str(post['date']))}</span>
          <span>&middot; {post['reading_time']} min read</span>
        </div>
        {desc}
        <div class="post-tags">{tags}</div>
      </a>'''
        )

    listing = (
        "\n".join(cards)
        if cards
        else '      <p class="empty">No posts yet. Drop a .docx in the '
        "<code>posts/</code> folder to publish.</p>"
    )

    (BLOG_DIR / "index.html").write_text(INDEX_TEMPLATE.format(cards=listing), encoding="utf-8")


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog | Nikhil Kumar</title>
  <meta name="description" content="Technical write-ups on data engineering, Spark, Kafka, and cloud architecture by Nikhil Kumar.">
  <link rel="canonical" href="https://nk2242696.github.io/blog/">
  <link rel="icon"
    href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%230a0a0a'/%3E%3Ctext x='50%25' y='50%25' dy='.1em' font-family='Inter,Arial,sans-serif' font-size='30' font-weight='700' fill='%23e50914' text-anchor='middle' dominant-baseline='middle'%3ENK%3C/text%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    :root {{
      --bg-primary: #0a0a0a;
      --bg-card: #1a1a2e;
      --bg-card-hover: #252541;
      --accent: #ffffff;
      --accent-muted: #b3b3b3;
      --accent-dim: #a1a1a6;
      --border: rgba(255, 255, 255, 0.08);
      --highlight: #e50914;
    }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-primary);
      color: var(--accent);
      line-height: 1.7;
      -webkit-font-smoothing: antialiased;
    }}

    .top-nav {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: rgba(10, 10, 10, 0.9);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border);
      padding: 1.2rem 5%;
    }}

    .top-nav a {{
      color: var(--accent-muted);
      font-size: 0.9rem;
      font-weight: 500;
      text-decoration: none;
      margin-right: 2rem;
    }}

    .top-nav a:hover {{ color: var(--accent); }}

    .blog-wrap {{ max-width: 900px; margin: 0 auto; padding: 5rem 5% 6rem; }}

    .blog-header {{ margin-bottom: 3rem; }}

    .blog-label {{
      font-size: 0.8rem;
      color: var(--highlight);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 2px;
      margin-bottom: 1rem;
    }}

    .blog-header h1 {{ font-size: 3rem; font-weight: 700; letter-spacing: -1px; }}

    .blog-header p {{ color: var(--accent-dim); margin-top: 1rem; font-size: 1.1rem; }}

    .post-list {{ display: grid; gap: 1.5rem; }}

    .post-card {{
      display: block;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 2.2rem;
      text-decoration: none;
      color: inherit;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    .post-card:hover {{
      background: var(--bg-card-hover);
      transform: translateY(-6px);
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6);
    }}

    .post-card h2 {{ font-size: 1.5rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0.6rem; }}

    .post-meta {{
      display: flex;
      gap: 0.8rem;
      color: var(--accent-dim);
      font-size: 0.85rem;
      margin-bottom: 0.8rem;
    }}

    .post-desc {{ color: var(--accent-muted); font-size: 0.98rem; margin-bottom: 1rem; }}

    .post-tags {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}

    .tag {{
      display: inline-block;
      padding: 0.3rem 0.9rem;
      background: rgba(229, 9, 20, 0.15);
      border: 1px solid rgba(229, 9, 20, 0.3);
      border-radius: 50px;
      color: var(--highlight);
      font-size: 0.78rem;
      font-weight: 600;
    }}

    .empty {{ color: var(--accent-dim); }}
    .empty code {{ background: rgba(255,255,255,0.08); padding: 0.15em 0.4em; border-radius: 5px; }}
  </style>
</head>

<body>
  <nav class="top-nav">
    <a href="/">&larr; Portfolio</a>
    <a href="/blog/">All posts</a>
  </nav>

  <main class="blog-wrap">
    <header class="blog-header">
      <div class="blog-label">Writing</div>
      <h1>Technical Blog</h1>
      <p>Notes on data engineering, Spark, Kafka, and cloud architecture.</p>
    </header>
    <div class="post-list">
{cards}
    </div>
  </main>
</body>

</html>
"""


def main() -> int:
    if not POSTS_DIR.exists():
        print(f"No posts directory at {POSTS_DIR}; nothing to build.")
        return 0

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    docx_files = sorted(POSTS_DIR.glob("*.docx"))

    posts: list[dict] = []
    for docx in docx_files:
        meta = load_meta(docx)
        slug = slugify(meta.get("slug") or docx.stem)
        words = word_count(docx)
        reading_time = max(1, round(words / WORDS_PER_MINUTE))

        print(f"Building {docx.name} -> blog/{slug}.html ({words} words, {reading_time} min)")
        render_post(docx, slug, meta, reading_time)

        posts.append(
            {
                "slug": slug,
                "title": meta["title"],
                "date": meta["date"],
                "tags": meta["tags"],
                "description": meta.get("description"),
                "reading_time": reading_time,
            }
        )

    render_index(posts)
    print(f"Done. {len(posts)} post(s) built.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
