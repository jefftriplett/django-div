# Markdown

The tree renders to Markdown as well as HTML, and Markdown can be read back
into a tree. Every example here is executed by `tests/test_markdown.py`.

```python
from django_div import Div, H1, P, from_html
from django_div.markdown import to_markdown

to_markdown(Div(H1("Title"), P("Body text.")))
# '# Title\n\nBody text.'
```

Because parsing produces the same kind of tree, `from_html` and
`to_markdown` compose into an HTML-to-Markdown converter:

```python
to_markdown(from_html("<article><h1>Title</h1><p>Body with <a href='/x'>a link</a>.</p></article>"))
# '# Title\n\nBody with [a link](/x).'
```

## What maps to what

| HTML | Markdown |
| --- | --- |
| `h1`–`h6` | `#` … `######` |
| `p` | paragraph |
| `em` / `i`, `strong` / `b` | `*x*`, `**x**` |
| `s` / `del` | `~~x~~` |
| `code`, `pre` | `` `x` ``, fenced block (language from `class="language-*"`) |
| `a`, `img` | `[text](href)`, `![alt](src)` — `title` included when present |
| `ul` / `ol` / `li` | `-` / `1.` items, nesting indented, `start=` honored |
| `blockquote` | `> ` prefixed lines |
| `table` | GFM pipe table — see [Tables](#tables) |
| `hr`, `br` | `---`, backslash hard break |
| `div`, `section`, … | invisible — children render as blocks |
| `span`, `mark`, … | invisible — children flow through inline |
| `script`, `style`, `head`, … | dropped |
| everything else | falls back to its HTML, which Markdown permits |

The tables driving this — `INLINE_WRAPPERS`, `CONTAINER_TAGS`,
`TRANSPARENT_TAGS`, `DROP_TAGS`, `HEADING_TAGS` — are module constants, so
teaching the renderer a new element is one dict or set entry.

## Lossy on purpose

Markdown has no home for `class`, `id`, `data-*`, or most other attributes,
so they are dropped. Text is emitted verbatim, not escaped, so content that
looks like Markdown syntax will be treated as Markdown by whatever renders
the output. Treat `to_markdown()` as a conversion, not an encoding:
round-trips preserve structure, not bytes.

## Tables

Tables get the fullest treatment, because they are where HTML-to-Markdown
conversions usually fall apart:

```python
Table(
    Caption("Prices"),
    Thead(Tr(Th("Item"), Th("Cost", style={"text_align": "right"}))),
    Tbody(Tr(Td("Apple"), Td("1"))),
)
```

```markdown
Prices

| Item | Cost |
| --- | --: |
| Apple | 1 |
```

- **Alignment** comes from `text-align` styles (string or mapping) or the
  legacy `align` attribute, and round-trips: `from_markdown` keeps the
  alignment markdown-it records, and `to_markdown` emits it back as
  `:--` / `:-:` / `--:`.
- **`thead` / `tbody` / `tfoot` render in that order**, matching how HTML
  displays them, even when the source declares them differently.
- **A caption** becomes a paragraph above the table — GFM has no caption.
- **A headerless table** gets an empty header row, since GFM requires one;
  the first data row is not promoted.
- **Hard breaks and block content in cells** flatten to `<br>`, which GFM
  permits, so a cell can never split its own row.
- **Nested tables** stay inside their cell as HTML, exactly once.
- **`colspan`/`rowspan` have no GFM form**, so such tables fall back to
  their HTML rather than silently misplacing data.

## Reading Markdown

`from_markdown()` returns the same kind of tree as `from_html()`. It
deliberately contains no Markdown parser: markdown-it-py renders CommonMark
plus GFM tables and strikethrough, and the HTML comes back through
`parse()`. Needs the `markdown` extra.

```python
from django_div.markdown import from_markdown

tree = from_markdown("# Title\n\nBody text.")
tree[0].tag          # 'h1'
tree[0].text         # 'Title'
```

```console
uv add 'django-div[markdown]'
```

## Fence and code edge cases

Content containing backticks can't break out of its own code span or fence —
the marker grows past it:

```python
to_markdown(Pre("a ``` b"))       # '````\na ``` b\n````'
to_markdown(P(Code("uses ` tick")))   # '`` uses ` tick ``'
```
