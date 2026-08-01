"""django_div - build and parse HTML in Python with Pydantic models.

Build a tree with the tag classes::

    >>> from django_div import Div, P, A
    >>> print(Div(P("Hello, World!"), A("Click", href="/x"), class_="card"))
    <div class="card"><p>Hello, World!</p><a href="/x">Click</a></div>

Or parse one back out of markup, and get the same kind of tree::

    >>> page = from_html('<div class="card"><a href="/x">Click</a></div>')
    >>> page.find("a").attrs["href"]
    '/x'

Text children are escaped. Void tags self-close. Attribute names are
normalized (``class_`` -> ``class``, ``data_id`` -> ``data-id``), ``True``
renders bare, and ``False``/``None`` drop the attribute entirely.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from html import escape
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, SerializeAsAny

__all__ = [
    "ATTR_OVERRIDES",
    "ITEM_CLASSES",
    "TAG_CLASSES",
    "VOID_TAGS",
    "Comment",
    "HtmlItem",
    "Raw",
    "Tag",
    "Text",
    "from_html",
    "normalize_attr",
    "parse",
    "tag_class",
    # Generated tag classes are appended at the bottom of this module.
]

__version__ = "0.1.0"


#: Attribute names whose Python spelling can't be derived by the normal rules.
ATTR_OVERRIDES = {
    "accept_charset": "accept-charset",
    "as_": "as",
    "async_": "async",
    "class_": "class",
    "del_": "del",
    "for_": "for",
    "http_equiv": "http-equiv",
    "in_": "in",
    "is_": "is",
}

#: Keys Pydantic passes back when it re-validates a serialized Tag.
FIELD_KEYS = frozenset({"attrs", "children", "tag", "type"})

#: Discriminator value -> class, for rebuilding leaves from a dump.
ITEM_CLASSES: dict[str, type[HtmlItem]] = {}

#: Tag name -> generated class, for rebuilding a typed tree from a dump.
TAG_CLASSES: dict[str, type[Tag]] = {}

#: HTML elements that never have children and render self-closed.
VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


def as_html_item(value: Any) -> Any:
    """Rebuild an HtmlItem from a plain dict, keeping its original class.

    Children are declared as HtmlItem, which has no fields of its own, so
    Pydantic would otherwise validate every child down to an empty base
    instance. The ``type`` discriminator picks the leaf class and ``tag``
    picks the element class, which makes model_dump/model_validate a real
    round trip.
    """
    if not isinstance(value, dict):
        return value
    if "tag" in value:
        cls = TAG_CLASSES.get(value["tag"], Tag)
        return cls(**value)
    cls = ITEM_CLASSES.get(value.get("type"))
    return cls(**value) if cls else value


def from_html(html: str, parser: str = "html.parser") -> Any:
    """Parse HTML, returning a single item when there is one root.

    Convenience wrapper over parse(), which always returns a list.
    """
    items = parse(html, parser)
    return items[0] if len(items) == 1 else items


def is_field_payload(children: tuple[Any, ...], attrs: dict[str, Any]) -> bool:
    """Is this ``__init__`` call Pydantic re-validating a serialized Tag?

    Defining ``__init__`` makes Pydantic v2 route validation through it, so
    ``Tag.model_validate({"tag": "div", ...})`` arrives looking like a call
    with an attribute named ``tag``. Requiring the ``attrs`` key too keeps
    real markup (``Div(tag="x")``) out of this branch.
    """
    return (
        not children
        and "attrs" in attrs
        and "tag" in attrs
        and FIELD_KEYS.issuperset(attrs)
    )


def iter_children(children: Iterable[Any]) -> Iterator[HtmlItem]:
    """Coerce arbitrary children into HtmlItems.

    ``None`` and ``False`` are dropped so inline conditionals work
    (``Div(user and P(user.name))``); lists, tuples, and generators are
    flattened so comprehensions can be splatted in; everything else is
    escaped as text.
    """
    for child in children:
        if child is None or child is False:
            continue
        if isinstance(child, HtmlItem):
            yield child
        elif isinstance(child, Iterable) and not isinstance(child, (str, bytes, dict)):
            yield from iter_children(child)
        else:
            yield Text(content=str(child))


def normalize_attr(name: str) -> str:
    """Turn a Python keyword name into its HTML attribute spelling.

    ``class_`` -> ``class``, ``data_test_id`` -> ``data-test-id``.
    """
    if name in ATTR_OVERRIDES:
        return ATTR_OVERRIDES[name]
    return name.removesuffix("_").replace("_", "-")


def parse(html: str, parser: str = "html.parser") -> list[HtmlItem]:
    """Parse an HTML string into a list of top-level items.

    The result is the same kind of tree the constructors build, so parsed
    markup can be searched, edited, re-rendered, or dumped to JSON::

        page = from_html(response.text)
        for link in page.find_all("a", target="_blank"):
            link.attrs["rel"] = "noopener"
        print(page)

    Requires beautifulsoup4. ``parser`` is handed to BeautifulSoup, so
    "lxml" or "html5lib" work if they are installed.
    """
    try:
        from bs4 import BeautifulSoup
        from bs4.element import Comment as SoupComment
        from bs4.element import Doctype, NavigableString
        from bs4.element import Tag as SoupTag
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise ImportError("parse() requires beautifulsoup4") from exc

    def convert(node: Any) -> HtmlItem | None:
        if isinstance(node, Doctype):
            return Raw(content=f"<!DOCTYPE {node}>")
        if isinstance(node, SoupComment):
            return Comment(content=str(node))
        if isinstance(node, NavigableString):
            return Text(content=str(node))
        if isinstance(node, SoupTag):
            attrs = {
                key: " ".join(value) if isinstance(value, list) else value
                for key, value in node.attrs.items()
            }
            cls = TAG_CLASSES.get(node.name)
            item = cls(**attrs) if cls else Tag(node.name, **attrs)
            item.children = convert_children(node.contents)
            return item
        return None

    def convert_children(nodes: list[Any]) -> list[HtmlItem]:
        items: list[HtmlItem] = []
        for index, node in enumerate(nodes):
            if is_blank_text(node):
                # Whitespace between two siblings is a word break, so keep one
                # space; source indentation around them is noise, so drop it.
                if 0 < index < len(nodes) - 1:
                    items.append(Text(content=" "))
                continue
            item = convert(node)
            if item is not None:
                items.append(item)
        return items

    def is_blank_text(node: Any) -> bool:
        is_plain_string = isinstance(node, NavigableString) and not isinstance(
            node, (SoupComment, Doctype)
        )
        return is_plain_string and not str(node).strip()

    return convert_children(BeautifulSoup(html, parser).contents)


def render_attrs(attrs: dict[str, Any]) -> str:
    """Render an attribute dict, leading space included, or ``""`` if empty."""
    parts = []
    for raw_name, value in attrs.items():
        if value is False or value is None:
            continue
        name = normalize_attr(raw_name)
        if value is True:
            parts.append(name)
            continue
        if name == "class":
            value = render_class(value)
        parts.append(f'{name}="{escape(str(value), quote=True)}"')
    return f" {' '.join(parts)}" if parts else ""


def render_class(value: Any) -> str:
    """Accept a string, an iterable, or a {name: bool} mapping for ``class``."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(name for name, keep in value.items() if keep)
    if isinstance(value, Iterable):
        return " ".join(str(item) for item in value if item)
    return str(value)


def tag_class(tag: str, name: str | None = None) -> type[Tag]:
    """Build a Tag subclass bound to one tag name, so ``Div(...)`` works.

    Defined as a subclass with a fixed ``__init__`` rather than a Pydantic
    field override, which v2 rejects on non-annotated attributes. The result
    is registered in TAG_CLASSES, so parsing knows about custom tags too.
    """
    name = name or tag.replace("-", "_").title().replace("_", "")

    def __init__(self, *children: Any, **attrs: Any) -> None:
        if is_field_payload(children, attrs):
            Tag.__init__(self, **attrs)
        else:
            Tag.__init__(self, tag, *children, **attrs)

    cls = type(
        name,
        (Tag,),
        {
            "__init__": __init__,
            "__doc__": f"The HTML <{tag}> element.",
            "__module__": __name__,
        },
    )
    TAG_CLASSES[tag] = cls
    return cls


class HtmlItem(BaseModel):
    """Base for anything that can appear in an HTML tree."""

    def __html__(self) -> str:
        """Mark output as safe for Django and Jinja2 templates."""
        return str(self)

    def render(self) -> str:
        """Render to a string, marked safe when Django is installed."""
        html = str(self)
        try:
            from django.utils.safestring import mark_safe
        except ImportError:
            return html
        return mark_safe(html)


class Comment(HtmlItem):
    """An HTML comment."""

    type: Literal["comment"] = "comment"
    content: str

    def __str__(self) -> str:
        return f"<!--{self.content.replace('--', '- -')}-->"


class Raw(HtmlItem):
    """Pre-trusted markup, passed through unescaped.

    Never build this from user input.
    """

    type: Literal["raw"] = "raw"
    content: str

    def __str__(self) -> str:
        return self.content


class Tag(HtmlItem):
    """An HTML element: a tag name, children, and attributes.

    Children are positional, attributes are keyword arguments::

        Tag("div", Tag("p", "hi"), class_="card")
    """

    type: Literal["tag"] = "tag"
    tag: str
    # SerializeAsAny keeps subclass fields in model_dump(); Pydantic v2
    # otherwise serializes each child against the declared HtmlItem schema,
    # which has no fields, so a tree would dump as a list of empty dicts.
    children: list[
        SerializeAsAny[Annotated[HtmlItem, BeforeValidator(as_html_item)]]
    ] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, _tag: str | None = None, *children: Any, **attrs: Any) -> None:
        if is_field_payload(children, attrs):
            super().__init__(**attrs)
            return
        super().__init__(
            tag=_tag,
            children=list(iter_children(children)),
            attrs={normalize_attr(key): value for key, value in attrs.items()},
        )

    @property
    def is_void(self) -> bool:
        return self.tag in VOID_TAGS

    @property
    def text(self) -> str:
        """All text in this subtree, unescaped."""
        return "".join(
            child.content if isinstance(child, Text) else child.text
            for child in self.children
            if isinstance(child, (Text, Tag))
        )

    def find(self, tag: str | None = None, **attrs: Any) -> Tag | None:
        """The first descendant tag matching, or None."""
        return next(iter(self.find_all(tag, **attrs)), None)

    def find_all(self, tag: str | None = None, **attrs: Any) -> list[Tag]:
        """Every descendant tag matching a name and/or attributes.

        Attribute names take the same Python spelling as the constructor::

            doc.find_all("a", class_="external")
        """
        wanted = {normalize_attr(key): value for key, value in attrs.items()}
        return [
            item
            for item in self.walk()
            if isinstance(item, Tag)
            and item is not self
            and (tag is None or item.tag == tag)
            and all(item.attrs.get(key) == value for key, value in wanted.items())
        ]

    def walk(self) -> Iterator[HtmlItem]:
        """Yield this item, then every descendant, depth first."""
        yield self
        for child in self.children:
            if isinstance(child, Tag):
                yield from child.walk()
            else:
                yield child

    def __call__(self, *children: Any) -> Tag:
        """Return a copy with more children, for building in stages."""
        clone = self.model_copy()
        clone.children = [*self.children, *iter_children(children)]
        return clone

    def __str__(self) -> str:
        attrs = render_attrs(self.attrs)
        if self.is_void:
            return f"<{self.tag}{attrs} />"
        children = "".join(str(child) for child in self.children)
        return f"<{self.tag}{attrs}>{children}</{self.tag}>"


class Text(HtmlItem):
    """A run of text. Escaped on render."""

    type: Literal["text"] = "text"
    content: str

    def __str__(self) -> str:
        return escape(self.content)


ITEM_CLASSES.update({"comment": Comment, "raw": Raw, "tag": Tag, "text": Text})

# Generated element classes. Names are capitalized to stay clear of builtins
# like `input`, `object`, and `map`.
_TAGS = [
    "a",
    "abbr",
    "address",
    "area",
    "article",
    "aside",
    "audio",
    "b",
    "base",
    "bdi",
    "bdo",
    "blockquote",
    "body",
    "br",
    "button",
    "canvas",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "data",
    "datalist",
    "dd",
    "details",
    "dfn",
    "dialog",
    "div",
    "dl",
    "dt",
    "em",
    "embed",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hgroup",
    "hr",
    "html",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "label",
    "legend",
    "li",
    "link",
    "main",
    "map",
    "mark",
    "menu",
    "meta",
    "meter",
    "nav",
    "noscript",
    "object",
    "ol",
    "optgroup",
    "option",
    "output",
    "p",
    "param",
    "picture",
    "pre",
    "progress",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "script",
    "search",
    "section",
    "select",
    "slot",
    "small",
    "source",
    "span",
    "strong",
    "style",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "template",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "title",
    "tr",
    "track",
    "u",
    "ul",
    "var",
    "video",
    "wbr",
]

for _tag in _TAGS:
    _cls = tag_class(_tag)
    globals()[_cls.__name__] = _cls
    __all__.append(_cls.__name__)

del _tag, _cls
