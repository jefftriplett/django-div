# django-div

Build and parse HTML in Python with Pydantic models.

```python
from django_div import A, Div, P

print(Div(P("Hello, World!"), A("Click", href="/x"), class_="card"))
```

```html
<div class="card"><p>Hello, World!</p><a href="/x">Click</a></div>
```

Children are positional, attributes are keyword arguments. Text is escaped,
void elements self-close, and Python attribute spellings map onto HTML ones.

## Why this exists

Most HTML-in-Python libraries build markup and stop there. Here the tree is a
Pydantic model, which means the same objects can go in three directions:

<div class="grid cards" markdown>

-   __Build__

    Compose elements as Python values, with escaping handled for you.

    [:octicons-arrow-right-24: Building HTML](building.md)

-   __Parse__

    Read existing markup back into the same tree, then search and edit it.

    [:octicons-arrow-right-24: Parsing HTML](parsing.md)

-   __Serialize__

    Round-trip a page through JSON with its element classes intact.

    [:octicons-arrow-right-24: Serializing](serializing.md)

-   __Render in Django__

    Components as templates, with escaping that works both ways.

    [:octicons-arrow-right-24: Django](django.md)

</div>

## Install

```console
uv add django-div            # building only
uv add 'django-div[parse]'   # plus from_html()/parse(), via bs4 + lxml
uv add 'django-div[html5]'   # spec-exact parsing, ~3x slower than lxml
```

Pydantic is the only hard dependency. Parsers are optional and their imports
are guarded, so building HTML pulls in nothing else. Django is optional too —
only `django_div.django` imports it.

## A tour in one page

```python
from django_div import Div, H1, Li, P, Span, Ul, from_html

# Nesting, attributes, escaping
Div(H1("Title"), P("a < b"), class_="page")
# <div class="page"><h1>Title</h1><p>a &lt; b</p></div>

# Falsy children drop out, so inline conditionals work
Div("Hello", user and Span(user.name))

# Collections flatten, so comprehensions splat in
Ul(Li(item) for item in items)

# Parse markup into the same kind of tree
page = from_html('<div><a href="/x" target="_blank">Click</a></div>')
page.find("a").attrs["href"]        # '/x'
page.text                           # 'Click'

# Edit it and render it back out
for link in page.find_all("a", target="_blank"):
    link.attrs["rel"] = "noopener"
print(page)
```

## llms.txt

This documentation is available in the [llms.txt](https://llmstxt.org/)
format, a Markdown convention suited to LLMs and AI coding assistants.

Two files are published:

- [`llms.txt`](https://django-div.readthedocs.io/en/latest/llms.txt): a short
  description of the project plus links to each section. The structure is
  described [here](https://llmstxt.org/#format).
- [`llms-full.txt`](https://django-div.readthedocs.io/en/latest/llms-full.txt):
  the same index with the content of every page inlined.

Every page is also published as Markdown alongside its HTML, so you can point
an assistant at a single section rather than the whole corpus. Append `.md` to
the page name:

```
https://django-div.readthedocs.io/en/latest/building.md
https://django-div.readthedocs.io/en/latest/django.md
```

## Where to next

- [Building HTML](building.md) — elements, attributes, escaping, categories
- [Parsing HTML](parsing.md) — `from_html()`, searching, editing, parsers
- [Serializing](serializing.md) — JSON round trips
- [Markdown](markdown.md) — render the tree as Markdown, read Markdown in
- [Django](django.md) — components as templates, escaping interop
- Cookbooks: [HTML](cookbook.md) · [Django](django-cookbook.md) ·
  [Markdown](markdown-cookbook.md)
- [API reference](reference.md) — every function, class, and constant
- [Contributing](contributing.md) — setup, conventions, tests

## Where it came from

django-div started as five throwaway scripts trying to answer one question:
how do you make `Div("hello", class_="x")` work when Pydantic wants keyword
fields? Those experiments are still in the git history at the
`Baseline: original django-div demo experiments` commit.

## Prior art

[htpy](https://htpy.dev), [dominate](https://github.com/Knio/dominate), and
[django-components](https://github.com/django-components/django-components)
cover adjacent ground, and htpy in particular landed on a very similar
constructor shape. django-div's angle is the Pydantic model underneath: the
same objects parse, validate, and serialize.
