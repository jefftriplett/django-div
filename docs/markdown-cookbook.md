# Markdown cookbook

Recipes built on `to_markdown()` and `from_markdown()`. Every example is
executed by `tests/test_markdown_cookbook.py`.

See [Markdown](markdown.md) for the mapping rules, and the
[Cookbook](cookbook.md) for HTML-side recipes.

## Writing

### One builder, two formats

A tree doesn't care which renderer consumes it, so the same function serves
the page as HTML and the export as Markdown:

```python
from django_div.markdown import to_markdown

table = data_table([{"name": "Ana", "age": 33}], ["name", "age"])
str(table)          # <table>...</table>              for the page
to_markdown(table)  # | name | age | ...              for the export
```

`data_table` is the [cookbook recipe](cookbook.md#a-table-from-data),
unchanged.

### A changelog from data

Markdown documents are trees too, so release notes come from the same
composition as any page:

```python
def changelog(releases):
    blocks = [H1("Changelog")]
    for version, date, changes in releases:
        blocks.append(H2(f"{version} ({date})"))
        blocks.append(Ul(Li(change) for change in changes))
    return to_markdown(blocks)

changelog([("1.1.0", "2026-08-01", ["Added X", "Fixed Y"])])
```

```markdown
# Changelog

## 1.1.0 (2026-08-01)

- Added X
- Fixed Y
```

### Convert scraped HTML to Markdown

```python
to_markdown(from_html("<article><h1>Post</h1><p>Text with <em>emphasis</em>.</p></article>"))
# '# Post\n\nText with *emphasis*.'
```

Feeding an LLM, archiving a page, filling a docs pipeline — one line. This
project's own `llms.txt` generator does exactly this conversion.

## Reading

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

### Markdown into a full page

The read tree drops straight into a layout, so a Markdown file becomes a
finished document:

```python
def page(markdown_text, *, title):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    return "".join(str(part) for part in [
        Doctype(),
        Html(
            Head(Meta(charset="utf-8"), Title(title)),
            Body(Div(items, class_="content")),
            lang="en",
        ),
    ])

page("# Hello\n\nWorld.", title="Hi")
# <!DOCTYPE html><html lang="en">...<div class="content"><h1>Hello</h1><p>World.</p></div>...
```

### Outline a document

```python
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

def outline(markdown_text):
    items = from_markdown(markdown_text)
    items = items if isinstance(items, list) else [items]
    return [
        (int(item.tag[1]), item.text)
        for item in items
        if isinstance(item, Tag) and item.tag in HEADINGS
    ]

outline("# A\n\ntext\n\n## B\n\n### C")   # [(1, 'A'), (2, 'B'), (3, 'C')]
```

### Extract every code block

Pull `(language, source)` pairs out of a document — the first step of
"run the examples in our docs as tests", which this project does:

```python
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

code_blocks("intro\n\n```python\nprint('hi')\n```\n\n```sql\nSELECT 1\n```")
# [('python', "print('hi')"), ('sql', 'SELECT 1')]
```

### Audit images for missing alt text

An accessibility check over content that lives as Markdown:

```python
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

images_missing_alt("![A cat](cat.png)\n\n![](bare.png)")   # ['bare.png']
```

## Round-tripping

### Merge documents, normalizing heading levels

Concatenating Markdown files naively produces colliding `#` levels. Read
each one, demote its headings under a section heading, and write the result
back out:

```python
def merged(docs):
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

merged([("Intro", "# Welcome\n\nHi."), ("Usage", "# Start")])
```

```markdown
# Handbook

## Intro

### Welcome

Hi.

## Usage

### Start
```
