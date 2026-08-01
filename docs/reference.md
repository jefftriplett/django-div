# API reference

## Conventions

Public functions take **at most one positional argument**; everything else is
keyword-only.

```python
from_html(markup, parser="lxml")     # not from_html(markup, "lxml")
```

Tag constructors reach the same place by a different route. Their positional
arguments are variadic children, and Python makes everything after `*children`
keyword-only, so anything you name is an attribute:

```python
Div(H1("Title"), P("Body"), class_="card")
#   \________ children ________/  \_ attrs _/
```

On the generic `Tag`, the element name is positional-**only**, which keeps
every possible attribute name free — including `tag` itself:

```python
Tag("div", tag="value")     # <div tag="value"></div>
Tag(_tag="div")             # TypeError
```

Tests enforce both halves across every element class, so this stays true.

## Items

All four item types inherit from `HtmlItem`.

### `Tag`

An element: a name, children, and attributes.

```python
Tag(name, *children, **attrs)
```

| Field | Meaning |
| --- | --- |
| `tag` | The element name |
| `children` | List of `HtmlItem` |
| `attrs` | Attributes, keys in HTML spelling |
| `type` | Discriminator, always `"tag"` |

**Properties**

`is_void`
:   Whether this element self-closes and forbids children.

`is_raw_text`
:   Whether content is emitted unescaped (`script`, `style`).

`text`
:   All text in the subtree, unescaped.

**Methods**

`find(tag=None, **attrs)`
:   First matching descendant, or `None`.

`find_all(tag=None, **attrs)`
:   Every matching descendant.

`walk()`
:   Yields this item then every descendant, depth first.

`render()`
:   The markup, as a `SafeString` when Django is installed.

`render_raw_text()`
:   Content of a raw text element. Raises if it contains the element's own
    closing tag.

`__call__(*children)`
:   A **copy** with more children appended.

`model_validate(obj)` / `model_validate_json(data)`
:   Load a tree, restoring element classes by their `tag`.

### `Text`

Escaped text. `Text(content="a < b")` renders `a &lt; b`.

### `Raw`

Unescaped markup. `Raw(content="<b>x</b>")` renders as-is.

!!! danger

    Never build a `Raw` from untrusted input.

### `Comment`

`Comment(content="note")` renders `<!--note-->`.

## Functions

`parse(html, *, parser=None)`
:   Parse into a list of top-level items. Needs the `parse` extra.

`from_html(html, *, parser=None)`
:   Like `parse()`, but unwraps a single root.

`best_parser()`
:   The best BeautifulSoup backend installed.

`tag_class(tag, *, name=None)`
:   Build and register a `Tag` subclass for one element name.

`normalize_attr(name)`
:   Python attribute spelling to HTML: `class_` to `class`.

`render_attrs(attrs)` / `render_class(value)` / `render_style(value)`
:   The attribute rendering helpers.

`iter_children(children)`
:   Coerce arbitrary values into items, applying the drop, flatten, trust,
    and escape rules.

`is_collection(value)`
:   Whether a value should be flattened as a group of children.

`marker()`
:   Django's `mark_safe` if installed, otherwise a passthrough.

## Constants

| Name | Contents |
| --- | --- |
| `TAG_CLASSES` | Tag name to class, including ones registered at runtime |
| `BUILTIN_TAGS` | The element names this library ships |
| `ITEM_CLASSES` | Discriminator to leaf class |
| `VOID_TAGS` | Elements that self-close |
| `RAW_TEXT_TAGS` | `script`, `style` |
| `PRE_TAGS` | `pre`, `textarea` |
| `DOCUMENT_TAGS` | `html`, `head`, `body` |
| `ATTR_OVERRIDES` | Irregular attribute spellings |
| `PARSERS` | Parser preference order |

## Element classes

Every element in the HTML living standard has a generated class, named after
the tag with a capital letter: `Div`, `P`, `H1`, `Textarea`, `Del`. Names are
capitalized so they never collide with builtins like `input`, `object`, or
`map`.

`param` is also included — obsolete, but still found in old documents.

Tests are parametrized over `TAG_CLASSES`, so every element is checked for
rendering, attributes, category behavior, and both round trips.

## `django_div.django`

`DjangoDivTemplates`
:   Template backend whose templates are dotted paths to callables.

`as_response(item, **kwargs)`
:   Render straight into an `HttpResponse`.

`csrf_input(request)`
:   The hidden CSRF field, as a `Raw`.

`render_component(component, *, context)`
:   Call a component with the parts of the context it declares.
