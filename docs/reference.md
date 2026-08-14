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
every possible attribute name free, including `tag` itself:

```python
Tag("div", tag="value")     # <div tag="value"></div>
Tag(_tag="div")             # TypeError
```

Tests enforce both halves across every element class, so this stays true.

## Items

All five item types inherit from `HtmlItem`.

### `Tag`

An element: a name, children, and attributes.

!!! note "Tag vs. element"

    MDN and the HTML spec would call this class an *element*. A tag is
    strictly just the `<div>` marker. The name follows BeautifulSoup, whose
    node class is also `Tag`, and everyday usage. The `.tag` field holds the
    element's tag name, which matches lxml's `Element.tag` exactly.

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

`iter_find(tag=None, **attrs)`
:   `find_all()` as a lazy iterator; `find()` uses it to stop at the first
    hit.

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

### `Doctype`

`Doctype()` renders `<!DOCTYPE html>`; `content` overrides what follows
`<!DOCTYPE`, for legacy identifiers. A `>` in the content would end the
declaration early, so rendering refuses it.

### `Comment`

`Comment(content="note")` renders `<!--note-->`. Comment syntax rules are
neutralized on render: `--` becomes `- -`, a leading `>`/`->` and a trailing
`-` are padded with a space. HTML5 would otherwise read the comment as
closed early and parse the remainder as live markup.

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
:   Python attribute spelling to HTML: `class_` to `class`. A trailing
    underscore is dropped, so any Python keyword works as `keyword_`.

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
| `VOID_ELEMENTS` | Elements that self-close |
| `RAW_TEXT_ELEMENTS` | `script`, `style` |
| `PRE_ELEMENTS` | `pre`, `textarea` |
| `DOCUMENT_ELEMENTS` | `html`, `head`, `body` |
| `ATTR_NAME_RE` | What a rendered attribute name may look like |
| `PARSERS` | Parser preference order |

## Element classes

Every element in the HTML living standard has a generated class, named after
the tag with a capital letter: `Div`, `P`, `H1`, `Textarea`, `Del`. Names are
capitalized so they never collide with builtins like `input`, `object`, or
`map`.

**114 elements** are generated, one for every element in the
[WHATWG HTML living standard](https://html.spec.whatwg.org/multipage/indices.html#elements-3)
including recent additions like `search` and `selectedcontent`, plus the
legacy `param`. Each class's docstring links to its
[MDN element reference](https://developer.mozilla.org/en-US/docs/Web/HTML/Element),
the best per-element documentation available, so `help(Div)` points at the
right page.

`param` is also included. It is obsolete, but still found in old documents.

Tests are parametrized over `TAG_CLASSES`, so every element is checked for
rendering, attributes, category behavior, and both round trips.

### All elements

The **Notes** column marks the three behavior sets: `void` elements
self-close and take no children, `raw text` content is never escaped, and
`pre` content keeps its whitespace verbatim.

| Class | Tag | Notes |
| --- | --- | --- |
| `A` | `<a>` |  |
| `Abbr` | `<abbr>` |  |
| `Address` | `<address>` |  |
| `Area` | `<area>` | void |
| `Article` | `<article>` |  |
| `Aside` | `<aside>` |  |
| `Audio` | `<audio>` |  |
| `B` | `<b>` |  |
| `Base` | `<base>` | void |
| `Bdi` | `<bdi>` |  |
| `Bdo` | `<bdo>` |  |
| `Blockquote` | `<blockquote>` |  |
| `Body` | `<body>` |  |
| `Br` | `<br>` | void |
| `Button` | `<button>` |  |
| `Canvas` | `<canvas>` |  |
| `Caption` | `<caption>` |  |
| `Cite` | `<cite>` |  |
| `Code` | `<code>` |  |
| `Col` | `<col>` | void |
| `Colgroup` | `<colgroup>` |  |
| `Data` | `<data>` |  |
| `Datalist` | `<datalist>` |  |
| `Dd` | `<dd>` |  |
| `Del` | `<del>` |  |
| `Details` | `<details>` |  |
| `Dfn` | `<dfn>` |  |
| `Dialog` | `<dialog>` |  |
| `Div` | `<div>` |  |
| `Dl` | `<dl>` |  |
| `Dt` | `<dt>` |  |
| `Em` | `<em>` |  |
| `Embed` | `<embed>` | void |
| `Fieldset` | `<fieldset>` |  |
| `Figcaption` | `<figcaption>` |  |
| `Figure` | `<figure>` |  |
| `Footer` | `<footer>` |  |
| `Form` | `<form>` |  |
| `H1` | `<h1>` |  |
| `H2` | `<h2>` |  |
| `H3` | `<h3>` |  |
| `H4` | `<h4>` |  |
| `H5` | `<h5>` |  |
| `H6` | `<h6>` |  |
| `Head` | `<head>` |  |
| `Header` | `<header>` |  |
| `Hgroup` | `<hgroup>` |  |
| `Hr` | `<hr>` | void |
| `Html` | `<html>` |  |
| `I` | `<i>` |  |
| `Iframe` | `<iframe>` |  |
| `Img` | `<img>` | void |
| `Input` | `<input>` | void |
| `Ins` | `<ins>` |  |
| `Kbd` | `<kbd>` |  |
| `Label` | `<label>` |  |
| `Legend` | `<legend>` |  |
| `Li` | `<li>` |  |
| `Link` | `<link>` | void |
| `Main` | `<main>` |  |
| `Map` | `<map>` |  |
| `Mark` | `<mark>` |  |
| `Menu` | `<menu>` |  |
| `Meta` | `<meta>` | void |
| `Meter` | `<meter>` |  |
| `Nav` | `<nav>` |  |
| `Noscript` | `<noscript>` |  |
| `Object` | `<object>` |  |
| `Ol` | `<ol>` |  |
| `Optgroup` | `<optgroup>` |  |
| `Option` | `<option>` |  |
| `Output` | `<output>` |  |
| `P` | `<p>` |  |
| `Param` | `<param>` | void |
| `Picture` | `<picture>` |  |
| `Pre` | `<pre>` | pre |
| `Progress` | `<progress>` |  |
| `Q` | `<q>` |  |
| `Rp` | `<rp>` |  |
| `Rt` | `<rt>` |  |
| `Ruby` | `<ruby>` |  |
| `S` | `<s>` |  |
| `Samp` | `<samp>` |  |
| `Script` | `<script>` | raw text |
| `Search` | `<search>` |  |
| `Section` | `<section>` |  |
| `Select` | `<select>` |  |
| `Selectedcontent` | `<selectedcontent>` |  |
| `Slot` | `<slot>` |  |
| `Small` | `<small>` |  |
| `Source` | `<source>` | void |
| `Span` | `<span>` |  |
| `Strong` | `<strong>` |  |
| `Style` | `<style>` | raw text |
| `Sub` | `<sub>` |  |
| `Summary` | `<summary>` |  |
| `Sup` | `<sup>` |  |
| `Table` | `<table>` |  |
| `Tbody` | `<tbody>` |  |
| `Td` | `<td>` |  |
| `Template` | `<template>` |  |
| `Textarea` | `<textarea>` | pre |
| `Tfoot` | `<tfoot>` |  |
| `Th` | `<th>` |  |
| `Thead` | `<thead>` |  |
| `Time` | `<time>` |  |
| `Title` | `<title>` |  |
| `Tr` | `<tr>` |  |
| `Track` | `<track>` | void |
| `U` | `<u>` |  |
| `Ul` | `<ul>` |  |
| `Var` | `<var>` |  |
| `Video` | `<video>` |  |
| `Wbr` | `<wbr>` | void |

## `django_div.markdown`

`to_markdown(item)`
:   Render an item or list of items as Markdown. No dependencies.

`from_markdown(text, *, parser=None)`
:   Read Markdown into a tree via markdown-it-py; needs the `markdown` extra.

`INLINE_WRAPPERS` / `HEADING_TAGS` / `CONTAINER_TAGS` / `TRANSPARENT_TAGS` / `DROP_TAGS`
:   The per-tag reference tables driving the renderer; extend them to teach
    it new elements.

## `django_div.django`

`DjangoDivTemplates`
:   Template backend whose templates are dotted paths to callables.

`as_response(item, **kwargs)`
:   Render straight into an `HttpResponse`.

`csrf_input(request)`
:   The hidden CSRF field, as a `Raw`.

`render_component(component, *, context)`
:   Call a component with the parts of the context it declares.
