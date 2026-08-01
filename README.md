# django-div

Build and parse HTML in Python with Pydantic models.

**[Documentation](https://jefftriplett.github.io/django-div/)**

```python
from django_div import A, Div, P

print(Div(P("Hello, World!"), A("Click", href="/x"), class_="card"))
# <div class="card"><p>Hello, World!</p><a href="/x">Click</a></div>
```

Children are positional, attributes are keyword arguments. Text is escaped,
void tags self-close, and Python attribute spellings map onto HTML ones
(`class_` → `class`, `data_test_id` → `data-test-id`). All 114 elements of
the [HTML living standard](https://developer.mozilla.org/en-US/docs/Web/HTML/Element)
ship as classes, with MDN links in their docstrings.

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

Comments neutralize HTML's comment-syntax rules on render, so content can
never close the comment early or leak out as live markup:

```python
Comment(content="note")   # <!--note-->
Comment(content="a--b")   # <!--a- -b-->   -- would end the comment
Comment(content=">boom")  # <!-- >boom-->  HTML5 reads <!--> as a whole comment
```

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

## Markdown

The same tree renders to Markdown, so `from_html` + `to_markdown` is an
HTML-to-Markdown converter, and `from_markdown()` reads Markdown into a tree
(via markdown-it-py, with the `markdown` extra):

```python
from django_div.markdown import from_markdown, to_markdown

to_markdown(from_html("<h1>Title</h1><p>Body</p>"))   # '# Title\n\nBody'
from_markdown("# Title")                              # H1(...)
```

Lossy by design: attributes have no Markdown home and are dropped.

## Django

Django is never imported unless it is installed, so it stays an optional
dependency.

### Components as templates

Register the backend and a component becomes addressable as a template:

```python
TEMPLATES = [
    {
        "BACKEND": "django_div.django.DjangoDivTemplates",
        "NAME": "django_div",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {"context_processors": [...]},
    },
    # your usual DjangoTemplates entry can stay alongside it
]
```

```python
# myapp/components.py
def home(title, **context):
    return Div(H1(title), class_="page")

# myapp/views.py
def home_view(request):
    return render(request, "myapp.components.home", {"title": "Hi"})
```

A component is any callable returning an `HtmlItem`. It receives the context
as keyword arguments — the whole context if it declares `**kwargs`, otherwise
only the parameters it names, so context processors can add `user` and friends
without breaking every signature.

### Without the template layer

```python
from django_div.django import as_response, csrf_input

def index(request):
    return as_response(Div(H1("Hi")))

def form_view(request):
    return as_response(Form(csrf_input(request), Input(name="q"), method="post"))
```

### Escaping

Rendering escapes text and attribute values, so output is safe markup by
construction and `{{ tag }}` works in a Django template with no `|safe`.
Interop runs both ways: anything with `__html__` — a `SafeString`, a
`markupsafe.Markup`, a rendered Django form — passes through a tag unescaped,
while plain strings are still escaped.

Lazy objects work too: `Div(gettext_lazy("Hello"))` resolves to one string
rather than one element per character.

## Install

```console
uv add django-div            # building only
uv add 'django-div[parse]'   # plus from_html()/parse(), via bs4 + lxml
uv add 'django-div[html5]'   # spec-exact parsing, ~3x slower than lxml
uv add 'django-div[markdown]' # plus from_markdown(), via markdown-it-py
```

Django is optional and never imported unless installed; `django_div.django`
is the only module that needs it.

## Development

```console
just bootstrap       # uv sync
just install-hooks   # prek install
just test            # pytest
just lint            # prek run --all-files
just docs            # serve the docs locally
just example         # run examples/example.py
```

## Prior art

[htpy](https://htpy.dev), [dominate](https://github.com/Knio/dominate), and
[django-components](https://github.com/django-components/django-components)
cover adjacent ground. django-div's angle is that the tree is a Pydantic
model, so the same objects parse, validate, and serialize.
