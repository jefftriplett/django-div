# Parsing HTML

`from_html()` turns markup back into the same tree the constructors build, so
a parsed page can be searched, edited, re-rendered, or serialized.

```console
uv add 'django-div[parse]'
```

```python
from django_div import from_html

page = from_html('<div class="card"><a href="/x">Click</a></div>')

type(page)                      # <class 'django_div.Div'>
page.find("a").attrs["href"]    # '/x'
page.text                       # 'Click'
```

## `parse()` and `from_html()`

`parse()` always returns a list of top-level items. `from_html()` unwraps the
single-root case, which is what you usually want.

```python
from django_div import parse

parse("<p>a</p><p>b</p>")       # [P(...), P(...)]
from_html("<p>a</p><p>b</p>")   # [P(...), P(...)]
from_html("<p>a</p>")           # P(...)
```

## Searching

```python
page.text                          # all text in the subtree, unescaped
page.find("a")                     # first matching descendant, or None
page.find("a", class_="external")  # match on attributes too
page.find_all("a")                 # every matching descendant
page.iter_find("a")                # the same, lazily
page.walk()                        # every node, depth first, including text
```

Attribute names use the same Python spellings as the constructors, so
`class_="external"` matches `class="external"`.

```python
for heading in page.find_all("h2"):
    print(heading.text)
```

## Editing

Parsed trees are ordinary models. Mutate `attrs`, append to `children`, then
render.

```python
page = from_html(response.text)

for link in page.find_all("a", target="_blank"):
    link.attrs["rel"] = "noopener"

print(page)
```

## Choosing a parser

Parsing goes through BeautifulSoup, which is a front end over several
backends. django-div picks the best one installed — `lxml`, then `html5lib`,
then the standard library — because they are not equivalent:

| Input | `html.parser` | `lxml` | `html5lib` |
| --- | --- | --- | --- |
| `<p>one<p>two` | `<p>one<p>two</p></p>` :material-close: | `<p>one</p><p>two</p>` | `<p>one</p><p>two</p>` |
| `<ul><li>a<li>b</ul>` | nested `<li>` :material-close: | correct | correct |
| 46 KB document | 28.8 ms | **17.8 ms** | 54.2 ms |

The standard library parser nests implicit closes instead of closing them,
which quietly produces a wrong tree, and it isn't the fastest either. It
remains the fallback because it needs no install.

Override per call when you need to:

```python
from_html(markup, parser="html5lib")
```

`best_parser()` reports what would be chosen.

## Fragments stay fragments

lxml and html5lib wrap a fragment in an invented `<html><body>` skeleton.
That would turn a parse-edit-render round trip into a rewrite, so django-div
strips wrappers the source did not ask for.

```python
from_html("<p>hi</p>")    # P(...), not Html(Body(P(...)))
```

If the source really does contain `<html>`, `<head>`, or `<body>`, those are
kept.

## Whitespace

Whitespace between two elements is a word break in the rendered page, so it
is preserved — collapsed to a single space, since the source indentation
itself carries no meaning.

```python
from_html("<p><b>a</b> <b>b</b></p>")
# <p><b>a</b> <b>b</b></p>          the space matters

from_html("<div>\n    <p>one</p>\n    <p>two</p>\n</div>")
# <div><p>one</p> <p>two</p></div>  indentation collapsed
```

Inside `pre` and `textarea`, whitespace is significant and kept verbatim.

## Comments and doctypes

Comments survive as `Comment` items and doctypes as `Doctype` items, so a
whole document round-trips:

```python
parse("<!DOCTYPE html><!--note--><p>hi</p>")
# [Doctype(...), Comment(...), P(...)]
```

`Doctype.content` is what follows `<!DOCTYPE` — `"html"` for modern
documents, or the full legacy identifier string when parsing old markup.

## Limits

Parsing is a tree conversion, not a browser. A few things to expect:

- Character references are resolved by the parser, so `&amp;` comes back as
  `&` and is re-escaped on render. The output is equivalent, not identical.
- Attribute order follows the source, but duplicate attributes are collapsed
  by the parser before django-div sees them.
- Malformed markup is repaired according to whichever backend is in use, so
  round-tripping broken HTML gives you the repaired version.
