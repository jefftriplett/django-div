"""Every recipe in docs/markdown-cookbook.md."""

from django_div import (
    H1,
    H2,
    Body,
    Div,
    Head,
    Html,
    Li,
    Meta,
    Raw,
    Tag,
    Title,
    Ul,
    from_html,
)
from django_div.markdown import from_markdown, to_markdown

# --- one builder, two formats ------------------------------------------------


def data_table(rows, columns):
    from django_div import Table, Tbody, Td, Th, Thead, Tr

    return Table(
        Thead(Tr(Th(column) for column in columns)),
        Tbody(Tr(Td(row[column]) for column in columns) for row in rows),
    )


def test_one_builder_two_formats():
    table = data_table([{"name": "Ana", "age": 33}], ["name", "age"])
    assert str(table).startswith("<table>")
    assert to_markdown(table) == "| name | age |\n| --- | --- |\n| Ana | 33 |"


# --- scraped html to markdown ------------------------------------------------


def test_convert_scraped_html_to_markdown():
    html = "<article><h1>Post</h1><p>Text with <em>emphasis</em>.</p></article>"
    assert to_markdown(from_html(html)) == "# Post\n\nText with *emphasis*."


# --- render user markdown, hardening links -----------------------------------


def render_user_markdown(text):
    items = from_markdown(text)
    items = items if isinstance(items, list) else [items]
    for item in items:
        if not isinstance(item, Tag):
            continue
        for link in item.find_all("a"):
            href = link.attrs.get("href", "")
            if href.startswith(("http://", "https://")):
                link.attrs["rel"] = "noopener"
                link.attrs["target"] = "_blank"
    return "".join(str(item) for item in items)


def test_render_user_markdown_hardens_external_links():
    html = render_user_markdown("[in](/x) and [out](https://ex.test)")
    assert '<a href="/x">in</a>' in html
    assert '<a href="https://ex.test" rel="noopener" target="_blank">out</a>' in html


# --- outline -----------------------------------------------------------------

HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def outline(markdown_text):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    return [
        (int(item.tag[1]), item.text)
        for item in items
        if isinstance(item, Tag) and item.tag in HEADINGS
    ]


def test_outline_of_a_markdown_document():
    assert outline("# A\n\ntext\n\n## B\n\n### C") == [(1, "A"), (2, "B"), (3, "C")]


# --- changelog generator -----------------------------------------------------


def changelog(releases):
    blocks = [H1("Changelog")]
    for version, date, changes in releases:
        blocks.append(H2(f"{version} ({date})"))
        blocks.append(Ul(Li(change) for change in changes))
    return to_markdown(blocks)


def test_changelog_generator():
    assert changelog([("1.1.0", "2026-08-01", ["Added X", "Fixed Y"])]) == (
        "# Changelog\n\n## 1.1.0 (2026-08-01)\n\n- Added X\n- Fixed Y"
    )


# --- extract code blocks -----------------------------------------------------


def code_blocks(markdown_text):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    found = []
    for item in items:
        if not (isinstance(item, Tag) and item.tag == "pre"):
            continue
        code = item.find("code") or item
        language = str(code.attrs.get("class", "")).removeprefix("language-")
        found.append((language, code.text.strip("\n")))
    return found


def test_extract_code_blocks():
    doc = "intro\n\n```python\nprint('hi')\n```\n\n```sql\nSELECT 1\n```"
    assert code_blocks(doc) == [("python", "print('hi')"), ("sql", "SELECT 1")]


# --- audit images for missing alt text ---------------------------------------


def images_missing_alt(markdown_text):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    return [
        img.attrs.get("src", "")
        for item in items
        if isinstance(item, Tag)
        for img in item.find_all("img")
        if not img.attrs.get("alt")
    ]


def test_images_missing_alt():
    doc = "![A cat](cat.png)\n\n![](bare.png)"
    assert images_missing_alt(doc) == ["bare.png"]


# --- markdown into a full page -----------------------------------------------


def page(markdown_text, *, title):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    return "".join(
        str(part)
        for part in [
            Raw(content="<!DOCTYPE html>"),
            Html(
                Head(Meta(charset="utf-8"), Title(title)),
                Body(Div(items, class_="content")),
                lang="en",
            ),
        ]
    )


def test_markdown_into_a_full_page():
    html = page("# Hello\n\nWorld.", title="Hi")
    assert html.startswith("<!DOCTYPE html>")
    assert "<title>Hi</title>" in html
    assert '<div class="content"><h1>Hello</h1><p>World.</p></div>' in html


# --- normalize heading levels when merging docs ------------------------------


def merged(docs):
    """Concatenate documents, demoting each one's headings under an H1."""
    blocks = []
    for title, text in docs:
        blocks.append(H2(title))
        items = from_markdown(text)
        items = items if isinstance(items, list) else [items]
        for item in items:
            if isinstance(item, Tag) and item.tag in HEADINGS:
                item.tag = f"h{min(int(item.tag[1]) + 2, 6)}"
            blocks.append(item)
    return to_markdown([H1("Handbook"), *blocks])


def test_merge_documents_normalizing_headings():
    result = merged([("Intro", "# Welcome\n\nHi."), ("Usage", "# Start")])
    assert result == (
        "# Handbook\n\n## Intro\n\n### Welcome\n\nHi.\n\n## Usage\n\n### Start"
    )
