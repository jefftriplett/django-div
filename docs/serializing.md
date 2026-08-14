# Serializing

Every item is a Pydantic model, so a tree dumps to a dict or JSON and loads
back with its element classes intact.

```python
from django_div import Div, P, Tag

tree = Div(P("hi"), class_="card")
payload = tree.model_dump_json()

restored = Tag.model_validate_json(payload)
str(restored) == str(tree)          # True
type(restored.children[0])          # <class 'django_div.P'>
```

## The shape

```python
Div(P("x"), class_="card").model_dump()
```

```python
{
    "type": "tag",
    "tag": "div",
    "attrs": {"class": "card"},
    "children": [
        {
            "type": "tag",
            "tag": "p",
            "attrs": {},
            "children": [{"type": "text", "content": "x"}],
        },
    ],
}
```

Two fields carry the type information:

`type`
:   Distinguishes the leaf kinds, which otherwise look identical: `Text`,
    `Raw`, and `Comment` all hold a single `content` string.

`tag`
:   Names the element, so `Div` comes back as `Div` rather than a generic
    `Tag`.

Attribute keys are stored in their **HTML** spelling, normalized when the
element is built. A hand-built tree and a parsed one are therefore
structurally identical.

```python
Div(class_="card").attrs == {"class": "card"}
```

## Loading

`Tag.model_validate()` and `Tag.model_validate_json()` dispatch on `tag`, so
you can load a tree without knowing what its root is.

```python
Tag.model_validate(payload)         # Div, P, whatever the root was
Div.model_validate(payload)         # forces Div, no dispatch
```

Unknown tags fall back to the generic `Tag`, which still renders correctly.
Registering the element first, with `tag_class()`, gets you the class back
instead.

## What this is good for

Serialization is the reason the models are Pydantic rather than plain
classes. It buys a few things that string-building alone doesn't:

- **Caching a rendered tree** as JSON, then reloading and patching part of it
  without re-parsing HTML.
- **Sending markup across a boundary** (a queue, an API) as structured data
  that can be validated on arrival rather than trusted as a string.
- **Diffing two versions of a page** structurally instead of textually.
- **Storing user-authored content** in a form you can inspect and constrain,
  rather than sanitizing HTML strings after the fact.

## Combining with parsing

Parsing and serializing compose, which is the whole point:

```python
from django_div import Tag, from_html

tree = from_html(response.text)     # HTML  -> models
payload = tree.model_dump_json()    # models -> JSON
tree = Tag.model_validate_json(payload)   # JSON -> models
print(tree)                         # models -> HTML
```
