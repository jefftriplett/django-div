# Markdown

The tree renders to Markdown as well as HTML, and Markdown reads back into
the same kind of tree. Every example on this page is executed by
`tests/test_markdown.py`.

```python
from django_div import Div, H1, P, from_html
from django_div.markdown import from_markdown, to_markdown

to_markdown(Div(H1("Title"), P("Body text.")))   # '# Title\n\nBody text.'
from_markdown("# Title")                         # H1(...)
```

`to_markdown()` needs nothing extra; `from_markdown()` needs the `markdown`
extra:

```console
uv add 'django-div[markdown]'
```

## Writing Markdown

`to_markdown()` takes one item, a list of items (what `parse()` and
`from_markdown()` return), or anything in between:

```python
to_markdown(H1("Title"))                    # '# Title'
to_markdown(Div(H1("Title"), P("Body")))    # blocks joined by blank lines
to_markdown([H1("A"), P("b")])              # '# A\n\nb'
```

Because parsing produces the same tree, `from_html` composes with it into an
HTML-to-Markdown converter:

```python
to_markdown(from_html("<article><h1>Title</h1><p>Body with <a href='/x'>a link</a>.</p></article>"))
# '# Title\n\nBody with [a link](/x).'
```

### What maps to what

| HTML | Markdown |
| --- | --- |
| `h1`–`h6` | `#` … `######` |
| `p` | paragraph |
| `em` / `i`, `strong` / `b` | `*x*`, `**x**` |
| `s` / `del` | `~~x~~` |
| `code`, `pre` | `` `x` ``, fenced block (language from `class="language-*"`) |
| `a`, `img` | `[text](href)`, `![alt](src)`; `title` included when present |
| `ul` / `ol` / `li` | `-` / `1.` items, nesting indented, `start=` honored |
| `blockquote` | `> ` prefixed lines |
| `table` | GFM pipe table; see [Tables](#tables) |
| `dl` / `dt` / `dd` | definition list; the term, then `:   definition` attached |
| `hr`, `br` | `---`, backslash hard break |
| `div`, `section`, … | invisible; children render as blocks |
| `span`, `mark`, … | invisible; children flow through inline |
| `script`, `style`, `head`, … | dropped |
| everything else | falls back to its HTML, which Markdown permits |

The tables driving this (`INLINE_WRAPPERS`, `CONTAINER_TAGS`,
`TRANSPARENT_TAGS`, `DROP_TAGS`, `HEADING_TAGS`) are module constants, so
teaching the renderer a new element is one dict or set entry.

#### Element tables

These three sets decide what happens to an element with no Markdown
equivalent. Everything absent from all of them falls back to its HTML.

| Constant | Effect | Elements |
| --- | --- | --- |
| `CONTAINER_TAGS` | rendered as blocks, the element disappears | `article`, `aside`, `body`, `details`, `dialog`, `div`, `fieldset`, `figure`, `footer`, `form`, `header`, `hgroup`, `html`, `main`, `menu`, `nav`, `search`, `section` |
| `TRANSPARENT_TAGS` | children flow through inline, no HTML fallback | `abbr`, `bdi`, `bdo`, `cite`, `data`, `dfn`, `kbd`, `label`, `mark`, `output`, `q`, `rp`, `rt`, `ruby`, `samp`, `slot`, `small`, `span`, `sub`, `sup`, `time`, `u`, `var` |
| `DROP_TAGS` | removed with their content | `head`, `link`, `meta`, `script`, `style`, `template`, `title` |

`INLINE_WRAPPERS` maps an inline element to a symmetric Markdown wrapper:

| Tag | Renders `x` as |
| --- | --- |
| `b` | `**x**` |
| `del` | `~~x~~` |
| `em` | `*x*` |
| `i` | `*x*` |
| `ins` | `x` (unwrapped) |
| `s` | `~~x~~` |
| `strong` | `**x**` |

`HEADING_TAGS` maps a heading to its prefix:

| Tag | Prefix |
| --- | --- |
| `h1` | `#` |
| `h2` | `##` |
| `h3` | `###` |
| `h4` | `####` |
| `h5` | `#####` |
| `h6` | `######` |

### Tables

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
- **A caption** becomes a paragraph above the table, because GFM has no caption.
- **A headerless table** gets an empty header row, since GFM requires one;
  the first data row is not promoted.
- **Hard breaks and block content in cells** flatten to `<br>`, which GFM
  permits, so a cell can never split its own row.
- **Nested tables** stay inside their cell as HTML, exactly once.
- **`colspan`/`rowspan` have no GFM form**, so such tables fall back to
  their HTML rather than silently misplacing data.

### Fences and code

Content containing backticks can't break out of its own code span or fence, because
the marker grows past it:

```python
to_markdown(Pre("a ``` b"))           # '````\na ``` b\n````'
to_markdown(P(Code("uses ` tick")))   # '`` uses ` tick ``'
```

### Lossy on purpose

Markdown has no home for `class`, `id`, `data-*`, or most other attributes,
so they are dropped. Text is emitted verbatim, not escaped, so content that
looks like Markdown syntax will be treated as Markdown by whatever renders
the output. Treat `to_markdown()` as a conversion, not an encoding:
round-trips preserve structure, not bytes.

## Reading Markdown

`from_markdown()` returns the same kind of tree as `from_html()`: typed
element classes, not a foreign AST. It deliberately contains no Markdown
parser: markdown-it-py renders CommonMark plus GFM tables and strikethrough,
and the HTML comes back through `parse()`.

```python
tree = from_markdown("# Title\n\nBody text.")
tree[0].tag          # 'h1'
tree[0].text         # 'Title'
```

A single-root document unwraps to the item itself, like `from_html()`;
anything else is a list.

### The tree is the point

Everything that works on a parsed HTML tree works on a parsed Markdown
document, including searching, editing, and serializing:

```python
doc = from_markdown("# Guide\n\nSee [the docs](/docs) and [the api](/api).")
[(a.text, a.attrs["href"]) for a in doc[1].find_all("a")]
# [('the docs', '/docs'), ('the api', '/api')]

from_markdown("# Title").model_dump()   # {'tag': 'h1', ...}
```

And because `to_markdown()` accepts the same tree back, Markdown documents
can be edited *structurally*, with no regexes over source text:

```python
doc = from_markdown("# Title\n\n## Section\n\nBody.")
for item in doc:
    if item.tag in ("h1", "h2"):
        item.tag = f"h{int(item.tag[1]) + 1}"   # demote one level

to_markdown(doc)   # '## Title\n\n### Section\n\nBody.'
```

### Fidelity

Reading then writing is stable: a second round trip reproduces the first,
and fenced code keeps its language and content exactly:

```python
doc = from_markdown("```python\nif a < b:\n    go()\n```")
doc.find("code").attrs["class"]   # 'language-python'
to_markdown(doc)                  # the same fence back, byte for byte
```

Alignment in tables survives the loop too. See [Tables](#tables).
