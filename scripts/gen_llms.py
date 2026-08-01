"""Generate per-page Markdown, llms.txt, and llms-full.txt from a built site.

Zensical has no plugin API yet (https://zensical.org/docs/community/faqs/) and
no llms.txt support, so this runs as a post-build step instead.

This works from the *rendered* HTML rather than docs/*.md on purpose. The docs
use Zensical syntax that means nothing outside the renderer: admonitions
(``!!! note``), grid cards, and content tabs would all reach a reader as raw
markers. Rendering first turns them into prose.

Page order, titles, and URLs come from zensical.toml, so adding a page to the
nav is the only step needed.

Usage: python scripts/gen_llms.py [site_dir]
"""

from __future__ import annotations

import os
import pathlib
import re
import sys
from html.parser import HTMLParser
from typing import ClassVar

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP = {"404"}


def config() -> dict:
    return tomllib.loads((ROOT / "zensical.toml").read_text())["project"]


def site_url(project: dict) -> str:
    """Canonical base URL, overridable so a preview build self-references."""
    return os.environ.get("SITE_URL", project.get("site_url", "")).rstrip("/")


def nav_order(project: dict) -> list[str]:
    """Page slugs in the order the nav declares them."""
    slugs = []
    for entry in project.get("nav", []):
        for filename in entry.values():
            slugs.append(pathlib.PurePosixPath(filename).stem)
    return slugs


class Extractor(HTMLParser):
    """Pull the <article> body out of a rendered page and re-emit Markdown."""

    BLOCK: ClassVar[set[str]] = {
        "p",
        "div",
        "section",
        "article",
        "ul",
        "ol",
        "table",
        "tr",
        "br",
    }
    HEADING: ClassVar[dict[str, int]] = {f"h{n}": n for n in range(1, 7)}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0  # >0 once inside <article>
        self.parts: list[str] = []
        self.title: str | None = None
        self._skip = 0  # inside nav/script/style
        self._pre = 0
        self._heading: int | None = None
        self._buf: list[str] = []
        self._code: list[str] = []
        self._lang = ""
        self._href: list[str] = []
        self.code: list[tuple[str, str]] = []
        self._table = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "nav"):
            self._skip += 1
            return
        # Skip permalink anchors and heading self-links.
        if tag == "a" and "headerlink" in (a.get("class") or ""):
            self._skip += 1
            return
        if tag == "article":
            self.depth += 1
            return
        if not self.depth or self._skip:
            return
        # Tables are collected cell by cell and re-emitted as Markdown at
        # </table>. Flowing them through as text loses the column boundaries.
        if tag == "table":
            self._table += 1
            self._rows = []
            return
        if self._table:
            if tag == "tr":
                self._row = []
            elif tag in ("th", "td"):
                self._cell = []
            return
        if tag == "pre":
            self._pre += 1
            self._code = []
        elif tag == "div" and "language-" in (a.get("class") or ""):
            # Zensical wraps highlighted blocks in
            # <div class="language-python highlight">; the language is only there.
            m = re.search(r"language-(\w+)", a["class"])
            self._lang = m.group(1) if m else ""
            self.parts.append("\n")
        elif tag == "a" and not self._pre:
            href = a.get("href") or ""
            self._href.append(href)
            if href:
                self.parts.append("[")
        elif tag in self.HEADING:
            self._heading = self.HEADING[tag]
            self._buf = []
        elif tag == "dt":
            self.parts.append("\n\n")
        elif tag == "dd":
            # Markdown definition-list syntax, so a term stays attached to
            # its description instead of running into the next term.
            self.parts.append("\n:   ")
        elif tag in self.BLOCK:
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav"):
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._skip:
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self.depth and not self._pre and self._href:
            href = self._href.pop()
            if href:
                self.parts.append(f"]({href})")
            return
        if tag == "article":
            self.depth = max(0, self.depth - 1)
            return
        if not self.depth or self._skip:
            return
        if tag == "table" and self._table:
            self._table -= 1
            if self._rows:
                self.parts.append(f"\n\n{self._render_table(self._rows)}\n\n")
            self._rows = []
            return
        if self._table:
            if tag in ("th", "td") and self._cell is not None:
                self._row = self._row if self._row is not None else []
                self._row.append(" ".join("".join(self._cell).split()))
                self._cell = None
            elif tag == "tr" and self._row is not None:
                self._rows.append(self._row)
                self._row = None
            return
        if tag == "dt":
            # No newline: the ":" line that follows must stay attached to the
            # term, or it stops being a definition list.
            return
        if tag == "dd":
            self.parts.append("\n")
            return
        if tag == "pre":
            self._pre = max(0, self._pre - 1)
            # Stash verbatim; whitespace normalisation below must not touch it,
            # or Python indentation in every example is destroyed.
            self.code.append((self._lang, "".join(self._code).strip("\n")))
            self.parts.append(f"\n\n\x00{len(self.code) - 1}\x00\n\n")
            self._code = []
        elif tag in self.HEADING and self._heading:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                if self.title is None and self._heading == 1:
                    self.title = text
                self.parts.append(f"\n\n{'#' * self._heading} {text}\n\n")
            self._heading = None
            self._buf = []

    def handle_data(self, data):
        if not self.depth or self._skip:
            return
        if self._table:
            if self._cell is not None:
                self._cell.append(data)
            return
        if self._heading:
            self._buf.append(data)
        elif self._pre:
            self._code.append(data)
        else:
            self.parts.append(re.sub(r"[ \t]*\n[ \t]*", " ", data))

    @staticmethod
    def _fence(lang: str, code: str) -> str:
        return f"```{lang}\n{code}\n```"

    @staticmethod
    def _render_table(rows: list[list[str]]) -> str:
        """Rows to a Markdown table, first row treated as the header."""
        width = max(len(row) for row in rows)
        padded = [
            [cell.replace("|", r"\|") for cell in row] + [""] * (width - len(row))
            for row in rows
        ]
        lines = [
            "| " + " | ".join(padded[0]) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]
        lines += ["| " + " | ".join(row) + " |" for row in padded[1:]]
        return "\n".join(lines)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]{2,}", " ", text)
        # Strip trailing whitespace per line first, so blank-line collapsing
        # below sees genuinely empty lines rather than lines of spaces.
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Restore code blocks after normalisation, fenced.
        text = re.sub(
            r"\x00(\d+)\x00", lambda m: self._fence(*self.code[int(m.group(1))]), text
        )
        return text.strip() + "\n"


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
        parser = Extractor()
        parser.feed(html_file.read_text(encoding="utf-8"))
        pages[slug] = (parser.title or slug, parser.markdown())
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
