# django-div

Build and parse HTML in Python with Pydantic models.

```python
from django_div import A, Div, P

print(Div(P("Hello, World!"), A("Click", href="/x"), class_="card"))
# <div class="card"><p>Hello, World!</p><a href="/x">Click</a></div>
```

Children are positional, attributes are keyword arguments. Text is escaped,
void tags self-close, and Python attribute spellings map onto HTML ones
(`class_` → `class`, `data_test_id` → `data-test-id`).

## Building

```python
Div(class_="card", data_id="1")          # <div class="card" data-id="1"></div>
Input(type="checkbox", checked=True)     # <input type="checkbox" checked />
Div(class_=["btn", "btn-primary"])       # <div class="btn btn-primary"></div>
Div(class_={"btn": True, "on": False})   # <div class="btn"></div>
Div("<script>x</script>")                # <div>&lt;script&gt;x&lt;/script&gt;</div>
```

`style` takes a mapping too, and `<script>`/`<style>` content is left
unescaped, since escaping it would change what the code means:

```python
Div(style={"color": "red", "font_size": "2rem"})
Script("if (a < b) { go() }")   # <script>if (a < b) { go() }</script>
```

Void elements raise rather than silently dropping children, and a raw-text
element refuses to render content containing its own closing tag.

`None` and `False` children drop out, so inline conditionals work. Lists and
generators flatten, so comprehensions splat in.

```python
Div("Hello", user and Span(user.name))
Ul(Li(item) for item in items)
```

Call a tag to append children and get a copy back, leaving the original alone:

```python
card = Div(class_="card")
card(H1("Title"), P("Body"))
```

`Tag` handles anything that isn't pre-generated, including custom elements:

```python
Tag("my-widget", "hi", data_state="ready")
```

## Parsing

`from_html()` returns the same kind of tree the constructors build, so parsed
markup can be searched, edited, and re-rendered. Needs the `parse` extra.

```python
page = from_html(response.text)

page.text                          # all text in the subtree
page.find("a", class_="external")  # first match, or None
page.find_all("a")                 # every descendant match
page.walk()                        # every node, depth first

for link in page.find_all("a", target="_blank"):
    link.attrs["rel"] = "noopener"

print(page)
```

`parse()` is the underlying function and always returns a list;
`from_html()` unwraps the single-root case.

Both pick the best parser installed — `lxml`, then `html5lib`, then the
stdlib. That matters: the stdlib parser turns `<p>one<p>two` into *nested*
paragraphs instead of closing the first, and lxml is also about 1.6x faster.
Pass `parser=` to override. Fragments stay fragments — the `<html><body>`
skeleton lxml and html5lib invent is stripped unless the source asked for it.

## Serializing

Trees are Pydantic models, so they round-trip through JSON with their classes
intact:

```python
payload = page.model_dump_json()
Tag.model_validate_json(payload)   # same tree, same subclasses
```

## Django

`HtmlItem.__html__()` satisfies the Django and Jinja2 safe-string protocol, so
tags drop into a template context without `|safe`. `.render()` returns a
`SafeString` when Django is installed and a plain `str` when it isn't — Django
is not a dependency.

## Install

```console
uv add django-div            # building only
uv add 'django-div[parse]'   # plus from_html()/parse(), via bs4 + lxml
uv add 'django-div[html5]'   # spec-exact parsing, ~3x slower than lxml
```

## Development

```console
just bootstrap       # uv sync
just install-hooks   # prek install
just test            # pytest
just lint            # prek run --all-files
just example         # run examples/example.py
```

## Prior art

[htpy](https://htpy.dev), [dominate](https://github.com/Knio/dominate), and
[django-components](https://github.com/django-components/django-components)
cover adjacent ground. django-div's angle is that the tree is a Pydantic
model, so the same objects parse, validate, and serialize.
