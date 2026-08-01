# Cookbook

Practical recipes, none of them Django-specific. Every example here is
executed by `tests/test_cookbook.py`, so what you see is what it produces.

For Django-specific recipes, see the [Django cookbook](django-cookbook.md).

## Building

### A reusable component

A component is a function. There is no registry, no base class, and no
special syntax — composition is a function call.

```python
def card(title, *body, href=None):
    heading = A(title, href=href) if href else title
    return Div(H2(heading), Div(*body, class_="card-body"), class_="card")

card("Hello", P("Body"), href="/x")
```

```html
<div class="card"><h2><a href="/x">Hello</a></h2><div class="card-body"><p>Body</p></div></div>
```

Taking `*body` and passing it through keeps the caller's syntax identical to
a built-in element's.

### A whole document

There is no `Doctype` element, because a doctype isn't one. Use `Raw` and
return a list:

```python
def document(title, *body, lang="en"):
    return [
        Raw(content="<!DOCTYPE html>"),
        Html(Head(Meta(charset="utf-8"), Title(title)), Body(*body), lang=lang),
    ]

def render(items):
    return "".join(str(item) for item in items)

render(document("Home", H1("Hi")))
```

```html
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8" /><title>Home</title></head><body><h1>Hi</h1></body></html>
```

### A table from data

```python
def data_table(rows, columns):
    return Table(
        Thead(Tr(Th(column) for column in columns)),
        Tbody(Tr(Td(row[column]) for column in columns) for row in rows),
    )

data_table([{"name": "Ana", "age": 33}], ["name", "age"])
```

```html
<table><thead><tr><th>name</th><th>age</th></tr></thead><tbody><tr><td>Ana</td><td>33</td></tr></tbody></table>
```

Nested generators work because each one is flattened as it is consumed.

### Navigation with an active item

A `class` mapping turns a condition into a class, and an all-false mapping
drops the attribute rather than emitting `class=""`.

```python
def nav(links, current):
    return Nav(
        Ul(Li(A(label, href=url, class_={"active": url == current}))
           for label, url in links)
    )

nav([("Home", "/"), ("Docs", "/docs/")], "/docs/")
```

```html
<nav><ul><li><a href="/">Home</a></li><li><a href="/docs/" class="active">Docs</a></li></ul></nav>
```

!!! warning "A generator can't sit beside a keyword argument"

    This is a Python rule, not a django-div one:

    ```python
    Ul(Li(x) for x in items, class_="errors")   # SyntaxError
    ```

    Add brackets and it's fine:

    ```python
    Ul([Li(x) for x in items], class_="errors")
    ```

### Custom elements and web components

```python
MyWidget = tag_class("my-widget")
MyWidget("hi", data_state="ready")
```

```html
<my-widget data-state="ready">hi</my-widget>
```

`tag_class()` registers the result **globally**, in `TAG_CLASSES`, so parsing
produces that class too. That is the point, but it means the registry grows at
runtime — `BUILTIN_TAGS` is the fixed set this library ships. For a one-off
that shouldn't be registered, `Tag("my-widget", ...)` skips it.

### SVG icons

SVG elements aren't generated, because SVG's `<text>` would collide with the
`Text` model. Build the ones you need:

```python
Svg = tag_class("svg")
Use = tag_class("use")

def icon(name, size=16):
    return Svg(
        Use(href=f"/static/icons.svg#{name}"),
        width=size, height=size, aria_hidden="true",
    )
```

```html
<svg width="16" height="16" aria-hidden="true"><use href="/static/icons.svg#check"></use></svg>
```

### XML, not just HTML

`Tag` doesn't care whether a name is HTML, so feeds and other XML work:

```python
Tag("rss",
    Tag("channel", Tag("title", "News"), Tag("item", Tag("title", "First"))),
    version="2.0")
```

```html
<rss version="2.0"><channel><title>News</title><item><title>First</title></item></channel></rss>
```

!!! note

    Only HTML void elements self-close, and HTML escaping rules are applied.
    For heavy XML work a dedicated library is a better fit.

## Parsing

These need the `parse` extra.

### Extract every link

```python
page = from_html(markup)
[(a.text, a.attrs["href"]) for a in page.find_all("a")]
```

```python
[("A", "/a"), ("B", "/b")]
```

### Make relative URLs absolute

```python
from urllib.parse import urljoin

def absolutize(tree, base):
    for link in tree.find_all("a"):
        if "href" in link.attrs:
            link.attrs["href"] = urljoin(base, link.attrs["href"])
    return tree

absolutize(from_html('<div><a href="/a">A</a></div>'), "https://example.test/")
```

```html
<div><a href="https://example.test/a">A</a></div>
```

### Build a table of contents

```python
def table_of_contents(tree, levels=("h2", "h3")):
    return Ul(
        Li(A(heading.text, href="#" + heading.attrs["id"]))
        for heading in tree.find_all()
        if heading.tag in levels and "id" in heading.attrs
    )
```

```html
<ul><li><a href="#a">A</a></li><li><a href="#b">B</a></li></ul>
```

Parsing and building in the same expression is the point: the input is HTML
and so is the output.

### Scrape a table into dicts

```python
def cells(row):
    return [cell.text.strip() for cell in row.find_all() if cell.tag in {"th", "td"}]

def table_to_dicts(table):
    rows = table.find_all("tr")
    headers = cells(rows[0])
    return [dict(zip(headers, cells(row))) for row in rows[1:]]
```

```python
[{"name": "Ana", "age": "33"}]
```

### Keep only certain elements

```python
KEEP = {"p", "b", "i", "em", "strong", "a", "ul", "ol", "li", "code", "br"}
KEEP_ATTRS = {"a": {"href", "title"}}
DROP_ENTIRELY = {"script", "style"}

def keep_only(items):
    kept = []
    for item in items:
        if isinstance(item, Text):
            kept.append(item)
        elif isinstance(item, Tag):
            if item.tag in DROP_ENTIRELY:
                continue
            if item.tag not in KEEP:
                kept.extend(keep_only(item.children))   # unwrap, keep content
                continue
            item.children = keep_only(item.children)
            item.attrs = {
                name: value for name, value in item.attrs.items()
                if name in KEEP_ATTRS.get(item.tag, set())
            }
            kept.append(item)
    return kept
```

```python
parse('<p onclick="evil()">ok <script>alert(1)</script><b>b</b></p>')
# -> <p>ok <b>b</b></p>
```

!!! danger "This is not a sanitizer"

    It is a shape filter for content you already trust — trimming a CMS
    export, normalizing pasted markup. It is **not** an XSS defense. Real
    sanitization has to handle `javascript:` URLs, CSS escapes, mutation
    XSS, and namespace confusion. For untrusted input use
    [nh3](https://pypi.org/project/nh3/) or
    [bleach](https://pypi.org/project/bleach/).

    Note that `DROP_ENTIRELY` exists because unwrapping a `<script>` would
    keep its *code* as visible text.

### Readable text

`.text` concatenates, matching the DOM's `textContent`, so adjacent blocks
run together:

```python
tree = from_html("<article><h1>Title</h1><p>one two</p></article>")
tree.text          # 'Titleone two'
```

When you want something readable — search indexing, summaries — join the
pieces yourself:

```python
def readable_text(tree, separator=" "):
    return separator.join(
        part for part in (
            item.content.strip() for item in tree.walk() if isinstance(item, Text)
        ) if part
    )

readable_text(tree)   # 'Title one two'
```

### Pretty-print a tree

Rendering has no indentation, by design. When you want it for debugging:

```python
def pretty(item, indent=0):
    pad = "  " * indent
    if not isinstance(item, Tag):
        text = str(item).strip()
        return [pad + text] if text else []
    if item.is_void:
        return [pad + str(item)]
    opening = str(item).split(">", 1)[0] + ">"
    lines = [pad + opening]
    for child in item.children:
        lines += pretty(child, indent + 1)
    return [*lines, pad + f"</{item.tag}>"]
```

```
<div>
  <p>
    hi
  </p>
</div>
```

## Markdown

These need the `markdown` extra for reading; writing needs nothing. See
[Markdown](markdown.md) for the full mapping.

### One builder, two formats

A tree doesn't care which renderer consumes it, so the `data_table` recipe
above serves the page as HTML and the export as Markdown:

```python
from django_div.markdown import to_markdown

table = data_table([{"name": "Ana", "age": 33}], ["name", "age"])
str(table)          # <table>...</table>          for the page
to_markdown(table)  # | name | age | ...          for the export
```

### Convert scraped HTML to Markdown

```python
to_markdown(from_html("<article><h1>Post</h1><p>Text with <em>emphasis</em>.</p></article>"))
# '# Post\n\nText with *emphasis*.'
```

Feeding an LLM, archiving a page, filling a docs pipeline — one line.

### Render user Markdown, hardening links on the way

Comments, bios, and READMEs arrive as Markdown; the page wants HTML with
house rules applied. Reading into a tree gives you an editing step between
the two:

```python
from django_div.markdown import from_markdown

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
```

```python
render_user_markdown("[in](/x) and [out](https://ex.test)")
# <p><a href="/x">in</a> and
#    <a href="https://ex.test" rel="noopener" target="_blank">out</a></p>
```

### Outline a Markdown document

```python
def outline(markdown_text):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    return [
        (int(item.tag[1]), item.text)
        for item in items
        if isinstance(item, Tag) and item.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
    ]

outline("# A\n\ntext\n\n## B\n\n### C")   # [(1, 'A'), (2, 'B'), (3, 'C')]
```

## Serializing

### Cache a parsed page

Parsing is the expensive part. Serialize once, reload cheaply:

```python
tree = from_html(response.text)
cache.set("page", tree.model_dump_json())

tree = Tag.model_validate_json(cache.get("page"))
```

Element classes survive the round trip, so `find_all()` and friends still
work on the way back.

### Compare two pages structurally

Models compare by value, so equality ignores nothing that matters and
nothing that doesn't:

```python
from_html("<div><p>x</p></div>") == from_html("<div><p>x</p></div>")   # True
from_html("<div><p>x</p></div>") == from_html("<div><p>y</p></div>")   # False
```

### Assert on structure, not strings

The most useful thing `from_html()` does in a test suite is let you stop
matching substrings:

```python
def test_search_form():
    page = from_html(response.text)
    assert page.find("input", name="q") is not None
    assert page.find("button").text == "Go"
```

That survives reformatting, attribute reordering, and added wrappers, all of
which break `assert '<input name="q">' in html`.
