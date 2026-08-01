# Building HTML

Every HTML element has a class, named after the tag with a capital letter:
`Div`, `P`, `H1`, `Textarea`. Children are positional arguments, attributes
are keyword arguments.

```python
from django_div import A, Div, H1, P

Div(
    H1("Welcome"),
    P("A paragraph with ", A("a link", href="/docs"), "."),
    class_="page",
)
```

```html
<div class="page"><h1>Welcome</h1><p>A paragraph with <a href="/docs">a link</a>.</p></div>
```

Rendering happens on `str()`, so `print(tag)`, f-strings, and
`"".join(...)` all work directly.

## Attributes

Python spellings are translated to HTML ones: a trailing underscore is
dropped, and remaining underscores become hyphens.

| Python | HTML |
| --- | --- |
| `class_="card"` | `class="card"` |
| `for_="email"` | `for="email"` |
| `data_test_id="hero"` | `data-test-id="hero"` |
| `aria_label="Close"` | `aria-label="Close"` |
| `hx_get="/rows"` | `hx-get="/rows"` |
| `http_equiv="refresh"` | `http-equiv="refresh"` |

Names that can't be derived by those rules live in `ATTR_OVERRIDES`.

### Boolean attributes

`True` renders the attribute bare. `False` and `None` drop it entirely, which
means you can pass a flag straight through.

```python
Input(type="checkbox", checked=is_selected, disabled=False)
```

```html
<input type="checkbox" checked />
```

### `class` and `style` take structures

`class` accepts a string, any iterable, or a mapping of name to condition:

```python
Div(class_="btn")                            # class="btn"
Div(class_=["btn", "btn-primary"])           # class="btn btn-primary"
Div(class_={"btn": True, "is-active": False})  # class="btn"
```

`style` accepts a string or a mapping, with property names normalized the
same way as attributes:

```python
Div(style={"color": "red", "font_size": "2rem"})
```

```html
<div style="color: red; font-size: 2rem"></div>
```

## Children

Anything that isn't already an element is converted to escaped text.

```python
P("a < b")        # <p>a &lt; b</p>
P(42)             # <p>42</p>
```

### Conditionals

`None` and `False` children are dropped, so `and`/`or` expressions work
inline without a temporary variable.

```python
Div(
    H1(title),
    user and P(f"Signed in as {user.name}"),
    error or None,
)
```

### Collections flatten

Lists, tuples, sets, ranges, and any iterator are flattened, so
comprehensions and generators splat in without unpacking.

```python
Ul(Li(item) for item in items)
Div([Span("a"), Span("b")])
```

!!! note "Why a whitelist and not `Iterable`"

    Strings are iterable, and so are Django's lazy translation proxies.
    Flattening everything iterable would turn `Div(gettext_lazy("Hi"))` into
    one text node per character. `is_collection()` names the types that
    actually mean "a group of children".

### Building in stages

Calling a tag returns a **copy** with the extra children appended, leaving
the original untouched. That makes a configured element reusable as a
prototype.

```python
card = Div(class_="card")

card(H1("First"))     # <div class="card"><h1>First</h1></div>
card(H1("Second"))    # <div class="card"><h1>Second</h1></div>
card                  # <div class="card"></div>
```

## Escaping

Text children and attribute values are escaped. This is not opt-in, so
untrusted content is safe by default.

```python
Div("<script>alert(1)</script>")
# <div>&lt;script&gt;alert(1)&lt;/script&gt;</div>

Div(title='he said "hi"')
# <div title="he said &quot;hi&quot;"></div>
```

To emit markup you have already vetted, wrap it in `Raw`:

```python
from django_div import Raw

Div(Raw(content="<b>bold</b>"))   # <div><b>bold</b></div>
```

!!! danger "Raw is a loaded gun"

    `Raw` bypasses escaping completely. Never build one from user input.

Anything implementing the `__html__` protocol — a Django `SafeString`, a
`markupsafe.Markup`, a rendered form — is trusted and passes through
unescaped, so interop with other libraries needs no special handling.

## Element categories

Three groups of elements behave differently, and django-div enforces the
difference rather than leaving it to you.

### Void elements

`br`, `img`, `input`, `hr`, and friends self-close and cannot have children.
Passing children raises instead of silently dropping them.

```python
Br()                          # <br />
Img(src="a.png", alt="A cat") # <img src="a.png" alt="A cat" />

Br("text")
# ValueError: <br> is a void element and cannot have children
```

### Raw text elements

`script` and `style` hold code, not text, so their content is **not**
escaped. Escaping it would change what the code means — `if (a < b)` is not
`if (a &lt; b)`.

```python
Script("if (a < b) { go() }")   # <script>if (a < b) { go() }</script>
Style("a > b { color: red }")   # <style>a > b { color: red }</style>
```

Because nothing escapes a raw text element except its own closing tag,
content containing that closing tag would break out of the element — and for
a `<script>`, the rest would run as markup. django-div refuses rather than
mangling it:

```python
str(Script("</script><script>alert(1)</script>"))
# ValueError: <script> content cannot contain '</script'; it would end the element
```

!!! warning "Interpolating into a script"

    Never build a `Script` from untrusted input. The closing-tag check stops
    the most obvious break-out, not every JavaScript injection. To pass data
    to the browser, render it as JSON into a `data-` attribute or a
    `<script type="application/json">` block instead.

### Preformatted elements

`pre` and `textarea` have significant whitespace. This only affects parsing —
see [Parsing HTML](parsing.md) — since building preserves exactly what you
pass.

## Elements not in the list

`Tag` takes the name as its first argument, and handles anything, including
custom elements and web components:

```python
from django_div import Tag

Tag("my-widget", "hi", data_state="ready")
# <my-widget data-state="ready">hi</my-widget>
```

To get a reusable class instead, use `tag_class()`. It registers the result,
so parsing will produce that class too:

```python
from django_div import tag_class

MyWidget = tag_class("my-widget")
MyWidget("hi", data_state="ready")
```
