"""Generate per-page Markdown, llms.txt, and llms-full.txt from a built site.

Zensical has no plugin API yet (https://zensical.org/docs/community/faqs/) and
no llms.txt support, so this runs as a post-build step instead.

This works from the *rendered* HTML rather than docs/*.md on purpose. The docs
use Zensical syntax that means nothing outside the renderer: admonitions
(``!!! note``), grid cards, and content tabs would all reach a reader as raw
markers. Rendering first turns them into prose.

The HTML-to-Markdown conversion itself is ``django_div.markdown.to_markdown``
over a ``parse()`` tree — the library run on its own docs, so a conversion
regression breaks this site's build before it reaches anyone else. This
script only selects the ``<article>``, prunes page furniture, and assembles
the llms.txt files.

Page order, titles, and URLs come from zensical.toml, so adding a page to the
nav is the only step needed.

Usage: python scripts/gen_llms.py [site_dir]
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

from django_div import Tag, parse
from django_div.markdown import to_markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP = {"404"}


def config() -> dict:
    return tomllib.loads((ROOT / "zensical.toml").read_text())["project"]


def site_url(project: dict) -> str:
    """Canonical base URL, overridable so a preview build self-references."""
    return os.environ.get("SITE_URL", project.get("site_url", "")).rstrip("/")


def nav_order(project: dict) -> list[str]:
    """Page slugs in the order the nav declares them, sections flattened."""

    def walk(entries: list) -> list[str]:
        slugs = []
        for entry in entries:
            for value in entry.values():
                if isinstance(value, list):  # a section: {"Cookbooks": [...]}
                    slugs += walk(value)
                else:
                    slugs.append(pathlib.PurePosixPath(value).stem)
        return slugs

    return walk(project.get("nav", []))


def article_of(items: list) -> Tag | None:
    """The <article> element of a rendered page: the content without chrome."""
    for item in items:
        if isinstance(item, Tag):
            if item.tag == "article":
                return item
            found = item.find("article")
            if found is not None:
                return found
    return None


def prune(tag: Tag) -> None:
    """Strip page furniture the Markdown twin should not carry.

    In-page <nav> and the ¶ permalink anchors are navigation, not content,
    and inline <svg> is decoration (twemoji icons) that would reach a reader
    as a screenful of path data. Zensical puts the language of a highlighted
    block only on its wrapper
    (``<div class="language-python highlight">``), so that class is pushed
    down onto the <pre>, where to_markdown()'s fence renderer looks for it.
    """
    kept = []
    for child in tag.children:
        if isinstance(child, Tag):
            if child.tag in ("nav", "svg"):
                continue
            if child.tag == "a" and "headerlink" in str(child.attrs.get("class", "")):
                continue
            if child.tag == "div" and "language-" in str(child.attrs.get("class", "")):
                pre = child.find("pre")
                if pre is not None:
                    pre.attrs.setdefault("class", child.attrs["class"])
            prune(child)
        kept.append(child)
    tag.children = kept


def convert(html: str) -> tuple[str | None, str]:
    """One rendered page as (title, markdown).

    The title is the first <h1>, and the body is everything inside
    <article>. A page without an article converts to nothing.
    """
    article = article_of(parse(html))
    if article is None:
        return None, ""
    prune(article)
    heading = article.find("h1")
    title = re.sub(r"\s+", " ", heading.text).strip() if heading else None
    return title, to_markdown(article).strip() + "\n"


def slug_of(page: pathlib.Path, site: pathlib.Path) -> str:
    rel = page.relative_to(site)
    return "index" if rel.parent == pathlib.Path(".") else rel.parent.as_posix()


def extract(site: pathlib.Path) -> dict[str, tuple[str, str]]:
    """Every rendered page, as {slug: (title, markdown)}."""
    pages = {}
    for html_file in site.rglob("index.html"):
        slug = slug_of(html_file, site)
        if slug in SKIP:
            continue
        title, body = convert(html_file.read_text(encoding="utf-8"))
        pages[slug] = (title or slug, body)
    return pages


def main() -> int:
    site = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    if not site.is_dir():
        print(f"error: {site} does not exist -- build the site first", file=sys.stderr)
        return 1

    project = config()
    base_url = site_url(project)
    name = project["site_name"]
    summary = project["site_description"]

    pages = extract(site)
    # The nav is the running order; anything it does not list is appended
    # alphabetically, so a new page still shows up without editing the nav.
    ordered = [slug for slug in nav_order(project) if slug in pages]
    ordered += sorted(set(pages) - set(ordered))

    index = [f"# {name}\n", f"> {summary}.\n", "## Docs\n"]
    full = [f"# {name}\n", f"> {summary}.\n"]

    for slug in ordered:
        title, body = pages[slug]
        # A Markdown twin next to every page: /building/ -> /building.md
        md_path = site / ("index.md" if slug == "index" else f"{slug}.md")
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(body, encoding="utf-8")

        url = f"{base_url}/" if slug == "index" else f"{base_url}/{slug}.md"
        index.append(f"- [{title}]({url})")
        full.append(f"\n---\n\n<!-- {slug} -->\n\n{body}")

    (site / "llms.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    (site / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

    words = len((site / "llms-full.txt").read_text().split())
    print(
        f"wrote llms.txt ({len(ordered)} pages), "
        f"llms-full.txt (~{words:,} words), and {len(ordered)} .md twins"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
