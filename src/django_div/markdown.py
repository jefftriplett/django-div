"""Markdown as a second renderer, and Markdown as input.

    >>> from django_div import Div, H1, P
    >>> from django_div.markdown import to_markdown
    >>> print(to_markdown(Div(H1("Title"), P("Body text."))))
    # Title
    <BLANKLINE>
    Body text.

Markdown is a lossy target: attributes like ``class`` and ``id`` have no
representation and are dropped, and text is emitted verbatim rather than
escaped. Elements with no Markdown equivalent fall back to their HTML, which
Markdown allows inline.

``from_markdown()`` deliberately does not parse Markdown itself: it renders
via markdown-it-py and reads the HTML back with parse(), so its output is the
same kind of tree everything else here uses.

Nothing in this module is imported by ``django_div`` itself.
"""

from __future__ import annotations

from typing import Any

from django_div import (
    Comment,
    Doctype,
    HtmlItem,
    Raw,
    Tag,
    Text,
)

__all__ = [
    "CONTAINER_TAGS",
    "DROP_TAGS",
    "HEADING_TAGS",
    "INLINE_WRAPPERS",
    "TRANSPARENT_TAGS",
    "from_markdown",
    "to_markdown",
]

#: Block-level elements with no Markdown equivalent: their children are
#: rendered as blocks and the element itself disappears.
CONTAINER_TAGS = frozenset(
    [
        "article",
        "aside",
        "body",
        "details",
        "dialog",
        "div",
        "fieldset",
        "figure",
        "footer",
        "form",
        "header",
        "hgroup",
        "html",
        "main",
        "menu",
        "nav",
        "search",
        "section",
    ]
)

#: Elements whose content means nothing in a document: dropped entirely.
DROP_TAGS = frozenset({"head", "link", "meta", "script", "style", "template", "title"})

#: Heading tag -> prefix.
HEADING_TAGS = {f"h{n}": "#" * n for n in range(1, 7)}

#: Inline elements that map to a symmetric Markdown wrapper. This is the
#: per-tag reference table; add entries to teach the renderer new inline
#: elements.
INLINE_WRAPPERS = {
    "b": ("**", "**"),
    "del": ("~~", "~~"),
    "em": ("*", "*"),
    "i": ("*", "*"),
    "ins": ("", ""),
    "s": ("~~", "~~"),
    "strong": ("**", "**"),
}

#: Inline elements with no Markdown equivalent whose children flow through
#: unchanged, rather than falling back to HTML.
TRANSPARENT_TAGS = frozenset(
    [
        "abbr",
        "bdi",
        "bdo",
        "cite",
        "data",
        "dfn",
        "kbd",
        "label",
        "mark",
        "output",
        "q",
        "rp",
        "rt",
        "ruby",
        "samp",
        "slot",
        "small",
        "span",
        "sub",
        "sup",
        "time",
        "u",
        "var",
    ]
)


def from_markdown(text: str, *, parser: str | None = None) -> Any:
    """Parse Markdown into a tree, via markdown-it-py.

    Requires the ``markdown`` extra. Returns a single item when the document
    has one root, otherwise a list, exactly like from_html().
    """
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise ImportError("from_markdown() requires markdown-it-py") from exc

    from django_div import parse

    # js-default: CommonMark plus GFM tables and strikethrough, no linkify.
    items = parse(MarkdownIt("js-default").render(text), parser=parser)
    # markdown-it separates blocks with newlines; between block elements that
    # whitespace is a rendering artifact, not content.
    items = [
        item
        for item in items
        if not (isinstance(item, Text) and not item.content.strip())
    ]
    return items[0] if len(items) == 1 else items


def to_markdown(item: HtmlItem | list[HtmlItem]) -> str:
    """Render a tree (or list of trees) as Markdown.

    Lossy by design: attributes without a Markdown home are dropped, and
    unrepresentable elements fall back to their HTML form.
    """
    items = item if isinstance(item, list) else [item]
    blocks = [rendered for i in items if (rendered := _block(i))]
    return "\n\n".join(blocks)


def _block(item: HtmlItem) -> str:
    """Render one block-level item; "" means it contributes nothing."""
    if isinstance(item, Doctype):
        return ""  # a doctype has no meaning in a Markdown document
    if isinstance(item, Text):
        return item.content.strip()
    if isinstance(item, Raw):
        return item.content.strip()
    if isinstance(item, Comment):
        return str(item)  # HTML comments are legal Markdown
    if not isinstance(item, Tag):
        return str(item)

    tag = item.tag
    if tag in DROP_TAGS:
        return ""
    if tag in CONTAINER_TAGS:
        return to_markdown(item.children)
    if tag in HEADING_TAGS:
        return f"{HEADING_TAGS[tag]} {_inline_children(item)}"
    if tag in ("p", "figcaption", "legend", "caption", "summary", "dt"):
        return _inline_children(item)
    if tag == "dd":
        return f":   {_inline_children(item)}"
    if tag == "dl":
        return _definition_list(item)
    if tag == "hr":
        return "---"
    if tag == "br":
        return ""
    if tag == "pre":
        return _fence(item)
    if tag == "blockquote":
        inner = to_markdown(item.children)
        return "\n".join(f"> {line}".rstrip() for line in inner.split("\n"))
    if tag in ("ul", "ol"):
        return _list(item)
    if tag == "table":
        return _table(item)
    if tag == "img":
        return _inline(item)
    # No block equivalent: fall back to inline handling, which itself falls
    # back to raw HTML for the truly unrepresentable.
    return _inline(item)


def _definition_list(tag: Tag) -> str:
    """A <dl> as definition-list groups.

    Not a plain container: joining dt and dd as sibling blocks would put a
    blank line between them, and a ``:`` line detached from its term stops
    being a definition list. Within a group the newline is single; between
    groups it is a blank line.
    """
    groups: list[list[str]] = []
    for child in tag.children:
        if not isinstance(child, Tag):
            continue
        if child.tag == "dt":
            groups.append([_inline_children(child)])
        elif child.tag == "dd":
            if not groups:
                groups.append([])
            groups[-1].append(f":   {_inline_children(child)}")
    return "\n\n".join("\n".join(group) for group in groups)


def _fence(pre: Tag) -> str:
    """A <pre> as a fenced code block, language taken from class=language-*."""
    language = ""
    source: Tag = pre
    child = next((c for c in pre.children if isinstance(c, Tag)), None)
    if child is not None and child.tag == "code":
        source = child
    for candidate in (source, pre, child):
        classes = str((candidate.attrs if candidate else {}).get("class", ""))
        for token in classes.split():
            if token.startswith("language-"):
                language = token.removeprefix("language-")
                break
        if language:
            break
    # Parsed <code> blocks carry a trailing newline; the fence adds its own.
    content = source.text.strip("\n")
    fence = "```"
    while fence in content:
        fence += "`"
    return f"{fence}{language}\n{content}\n{fence}"


def _inline(item: HtmlItem) -> str:
    """Render one item in inline context."""
    if isinstance(item, Text):
        return item.content
    if isinstance(item, Raw):
        return item.content
    if isinstance(item, Comment):
        return str(item)
    if not isinstance(item, Tag):
        return str(item)

    tag = item.tag
    if tag in DROP_TAGS:
        return ""
    if tag in TRANSPARENT_TAGS:
        return _inline_children(item)
    if tag in INLINE_WRAPPERS:
        before, after = INLINE_WRAPPERS[tag]
        return f"{before}{_inline_children(item)}{after}"
    if tag == "a":
        href = item.attrs.get("href", "")
        title = item.attrs.get("title")
        target = f'{href} "{title}"' if title else href
        return f"[{_inline_children(item)}]({target})"
    if tag == "img":
        alt = item.attrs.get("alt", "")
        src = item.attrs.get("src", "")
        title = item.attrs.get("title")
        target = f'{src} "{title}"' if title else src
        return f"![{alt}]({target})"
    if tag == "br":
        return "\\\n"
    if tag == "code":
        content = item.text
        marker = "`"
        while marker in content:
            marker += "`"
        if marker != "`":
            # CommonMark: pad so a leading/trailing backtick in the content
            # cannot merge with the marker; renderers strip one space back.
            content = f" {content} "
        return f"{marker}{content}{marker}"
    # No Markdown form at all: keep the HTML, which Markdown permits inline.
    return str(item)


def _inline_children(item: Tag) -> str:
    return "".join(_inline(child) for child in item.children)


def _list(tag: Tag, *, indent: int = 0) -> str:
    """A <ul>/<ol> as list items, nested lists indented four spaces."""
    ordered = tag.tag == "ol"
    number = int(tag.attrs.get("start", 1))
    pad = " " * indent
    lines = []
    for child in tag.children:
        if not (isinstance(child, Tag) and child.tag == "li"):
            continue
        marker = f"{number}. " if ordered else "- "
        nested = [
            grandchild
            for grandchild in child.children
            if isinstance(grandchild, Tag) and grandchild.tag in ("ul", "ol")
        ]
        own = [grandchild for grandchild in child.children if grandchild not in nested]
        parts: list[str] = []
        for grandchild in own:
            if isinstance(grandchild, Tag) and (
                grandchild.tag == "p" or grandchild.tag in CONTAINER_TAGS
            ):
                # Blocks inside a list item flatten onto the item's line:
                # markdown-it renders every loose list as <li><p>...</p></li>,
                # so treating <p> as unrepresentable would emit raw HTML for
                # ordinary round-tripped lists.
                if parts:
                    parts.append(" ")
                parts.append(_inline_children(grandchild))
            else:
                parts.append(_inline(grandchild))
        first = "".join(parts).strip()
        lines.append(f"{pad}{marker}{first}")
        lines.extend(_list(sub, indent=indent + 4) for sub in nested)
        number += 1
    return "\n".join(lines)


def _table(tag: Tag) -> str:
    """A <table> as a GFM pipe table.

    Header and alignment come from the thead/th cells, thead/tbody/tfoot
    render in that order regardless of source order, a caption becomes a
    paragraph above the table, and a headerless table gets an empty header
    row rather than having its first data row promoted. Tables using
    colspan/rowspan have no GFM form and fall back to their HTML.
    """
    caption, head_rows, body_rows, foot_rows = _table_parts(tag)
    all_rows = head_rows + body_rows + foot_rows
    for row in all_rows:
        for cell in _table_cells(row):
            if "colspan" in cell.attrs or "rowspan" in cell.attrs:
                return str(tag)

    header_cells: list[Tag] = []
    if head_rows:
        header_cells = _table_cells(head_rows[0])
        data_rows = head_rows[1:] + body_rows + foot_rows
    elif body_rows and any(cell.tag == "th" for cell in _table_cells(body_rows[0])):
        header_cells = _table_cells(body_rows[0])
        data_rows = body_rows[1:] + foot_rows
    else:
        data_rows = body_rows + foot_rows

    rendered = [[_table_cell(cell) for cell in header_cells]] if header_cells else []
    rendered += [[_table_cell(cell) for cell in _table_cells(row)] for row in data_rows]
    rendered = [row for row in rendered if row]
    if not rendered:
        return ""
    width = max(len(row) for row in rendered)
    padded = [row + [""] * (width - len(row)) for row in rendered]

    if header_cells:
        header, *data = padded
        separator = [_table_alignment(cell) for cell in header_cells]
        separator += ["---"] * (width - len(separator))
    else:
        # GFM requires a header row; an empty one keeps data as data.
        header, data = [""] * width, padded
        separator = ["---"] * width

    lines = ["| " + " | ".join(header) + " |"]
    lines += ["| " + " | ".join(separator) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in data]
    table = "\n".join(lines)
    if caption is not None:
        return f"{_inline_children(caption)}\n\n{table}"
    return table


def _table_alignment(cell: Tag) -> str:
    """A GFM separator token from a cell's text-align style or align attr."""
    style = cell.attrs.get("style", "")
    if isinstance(style, dict):
        style = ";".join(f"{name}:{value}" for name, value in style.items())
    normalized = str(style).replace(" ", "").replace("_", "-").lower()
    align = str(cell.attrs.get("align", "")).lower()
    if "text-align:center" in normalized or align == "center":
        return ":-:"
    if "text-align:right" in normalized or align == "right":
        return "--:"
    if "text-align:left" in normalized or align == "left":
        return ":--"
    return "---"


def _table_cell(cell: Tag) -> str:
    """One cell as a single line: hard breaks become <br>, pipes escaped."""
    parts = []
    for child in cell.children:
        if isinstance(child, Tag) and child.tag == "br":
            parts.append("<br>")
        elif isinstance(child, Tag) and (
            child.tag in CONTAINER_TAGS or child.tag == "p"
        ):
            # A block inside a cell has to flatten; <br> keeps the break.
            if parts:
                parts.append("<br>")
            parts.append(_inline_children(child))
        else:
            parts.append(_inline(child))
    text = "".join(parts).replace("\\\n", "<br>")
    return " ".join(text.split()).replace("|", r"\|")


def _table_cells(row: Tag) -> list[Tag]:
    return [
        cell
        for cell in row.children
        if isinstance(cell, Tag) and cell.tag in ("td", "th")
    ]


def _table_parts(
    tag: Tag,
) -> tuple[Tag | None, list[Tag], list[Tag], list[Tag]]:
    """Split a table into caption and thead/body/tfoot rows.

    Only direct structure is read, never find_all, so rows of a nested
    table stay inside their own table instead of leaking into this one.
    """
    caption = None
    head_rows: list[Tag] = []
    body_rows: list[Tag] = []
    foot_rows: list[Tag] = []
    for child in tag.children:
        if not isinstance(child, Tag):
            continue
        if child.tag == "caption":
            caption = child
        elif child.tag == "tr":
            body_rows.append(child)
        elif child.tag in ("thead", "tbody", "tfoot"):
            rows = [
                row
                for row in child.children
                if isinstance(row, Tag) and row.tag == "tr"
            ]
            if child.tag == "thead":
                head_rows += rows
            elif child.tag == "tfoot":
                foot_rows += rows
            else:
                body_rows += rows
    return caption, head_rows, body_rows, foot_rows
