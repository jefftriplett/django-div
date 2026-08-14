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

import json
import re
from collections.abc import Callable, Iterable, Iterator
from functools import cache
from html import escape
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, SerializeAsAny

__all__ = [
    "ATTR_NAME_RE",
    "BUILTIN_TAGS",
    "DOCUMENT_ELEMENTS",
    "ITEM_CLASSES",
    "PARSERS",
    "PRE_ELEMENTS",
    "RAW_TEXT_ELEMENTS",
    "TAG_CLASSES",
    "VOID_ELEMENTS",
    "Comment",
    "Doctype",
    "HtmlItem",
    "Raw",
    "Tag",
    "Text",
    "best_parser",
    "from_html",
    "is_collection",
    "marker",
    "normalize_attr",
    "parse",
    "tag_class",
    # Generated tag classes are appended at the bottom of this module.
]

# CalVer, YYYY.M.N: month and micro unpadded, micro 1-based per release
# within the month. Adopted before anything shipped to PyPI, so no 0.x or
# SemVer number ever appears there.
__version__ = "2026.8.1"


#: What an attribute name may look like, per the WHATWG HTML syntax rules:
#: no whitespace, quotes, ``>``, ``/``, ``=``, or control characters. Values
#: are escaped on render; names cannot be, so a name that fails this pattern
#: could smuggle a second attribute into the output and must be refused.
ATTR_NAME_RE = re.compile(r'^[^\s"\'>/=\x00-\x1f\x7f]+$')

#: Wrappers a parser may invent around a fragment.
DOCUMENT_ELEMENTS = frozenset({"body", "head", "html"})

#: Keys Pydantic passes back when it re-validates a serialized Tag.
FIELD_KEYS = frozenset({"attrs", "children", "tag", "type"})

#: Discriminator value -> class, for rebuilding leaves from a dump.
ITEM_CLASSES: dict[str, type[HtmlItem]] = {}

#: Parsers to try, best first. lxml is both faster and more correct than the
#: stdlib parser, which nests implicit closes (``<p>a<p>b``) instead of
#: closing them.
PARSERS = ("lxml", "html5lib", "html.parser")

#: Elements whose text content is significant, so parsing keeps it verbatim.
PRE_ELEMENTS = frozenset({"pre", "textarea"})

#: Elements whose content is raw text, never HTML-escaped on render. Escaping
#: these would corrupt them: ``if (a < b)`` is not ``if (a &lt; b)``.
RAW_TEXT_ELEMENTS = frozenset({"script", "style"})

#: Tag name -> generated class, for rebuilding a typed tree from a dump.
TAG_CLASSES: dict[str, type[Tag]] = {}

#: HTML elements that never have children and render self-closed.
VOID_ELEMENTS = frozenset(
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


@cache
def marker() -> Callable[[str], str]:
    """Django's mark_safe if it is installed, otherwise a passthrough.

    Rendering escapes text and attribute values, so output is safe markup by
    construction. Saying so matters in a Django template: ``{{ tag }}`` calls
    ``str()`` on anything that is not already a str *before* it looks for
    ``__html__``, so returning a plain str would get the markup escaped.
    """
    try:
        from django.utils.safestring import mark_safe
    except ImportError:
        return lambda value: value
    return mark_safe


@cache
def best_parser() -> str:
    """The best BeautifulSoup backend installed, preferring correctness.

    Cached: the answer cannot change within a process, and find_spec is too
    slow to pay on every parse() call.
    """
    from importlib.util import find_spec

    for parser in PARSERS:
        if parser == "html.parser" or find_spec(parser.split(".")[0]):
            return parser
    return "html.parser"  # pragma: no cover - html.parser is always present


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


def from_html(html: str, *, parser: str | None = None) -> Any:
    """Parse HTML, returning a single item when there is one root.

    Convenience wrapper over parse(), which always returns a list.
    """
    items = parse(html, parser=parser)
    return items[0] if len(items) == 1 else items


def is_collection(value: Any) -> bool:
    """Is this a group of children to flatten, rather than one child?

    Deliberately a whitelist. Testing for Iterable would walk anything with
    ``__iter__``, and Django's lazy translation proxies have one, so
    ``Div(gettext_lazy("Hi"))`` would render one Text per character.
    """
    return isinstance(value, (list, tuple, set, frozenset, Iterator, range))


def is_field_payload(children: tuple[Any, ...], *, attrs: dict[str, Any]) -> bool:
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
    (``Div(user and P(user.name))``); collections are flattened so
    comprehensions can be splatted in; anything implementing ``__html__``
    (a Django SafeString, a markupsafe Markup) is trusted as markup; and
    everything else is escaped as text.
    """
    for child in children:
        if child is None or child is False:
            continue
        if isinstance(child, HtmlItem):
            yield child
        elif hasattr(child, "__html__"):
            # Already-safe markup from Django, Jinja2, or another library.
            yield Raw(content=child.__html__())
        elif is_collection(child):
            yield from iter_children(child)
        else:
            # str() resolves lazy objects, such as Django's gettext_lazy.
            yield Text(content=str(child))


def normalize_attr(name: str) -> str:
    """Turn a Python keyword name into its HTML attribute spelling.

    ``class_`` -> ``class``, ``data_test_id`` -> ``data-test-id``. One
    trailing underscore is dropped, so every Python keyword is reachable as
    ``keyword_``; the remaining underscores become hyphens.
    """
    return name.removesuffix("_").replace("_", "-")


def parse(html: str, *, parser: str | None = None) -> list[HtmlItem]:
    """Parse an HTML string into a list of top-level items.

    The result is the same kind of tree the constructors build, so parsed
    markup can be searched, edited, re-rendered, or dumped to JSON::

        page = from_html(response.text)
        for link in page.find_all("a", target="_blank"):
            link.attrs["rel"] = "noopener"
        print(page)

    Requires beautifulsoup4. ``parser`` is handed to BeautifulSoup; it
    defaults to the best backend installed, see best_parser().
    """
    try:
        from bs4 import BeautifulSoup
        from bs4.element import Comment as SoupComment
        from bs4.element import Doctype as SoupDoctype
        from bs4.element import NavigableString
        from bs4.element import Tag as SoupTag
    except ImportError as exc:  # pragma: no cover - depends on install extras
        raise ImportError("parse() requires beautifulsoup4") from exc

    # Elements are converted shallow and their children attached from this
    # queue afterwards, so document depth is not bounded by the Python stack.
    pending: list[tuple[Any, Tag, bool]] = []

    def convert(node: Any, *, verbatim: bool = False) -> HtmlItem | None:
        if isinstance(node, SoupDoctype):
            return Doctype(content=str(node))
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
            pending.append((node, item, verbatim))
            return item
        return None

    def convert_children(nodes: list[Any], *, verbatim: bool = False) -> list[HtmlItem]:
        items: list[HtmlItem] = []
        for index, node in enumerate(nodes):
            if not verbatim and is_blank_text(node):
                # Whitespace between two siblings is a word break, so keep one
                # space; source indentation around them is noise, so drop it.
                if 0 < index < len(nodes) - 1:
                    items.append(Text(content=" "))
                continue
            item = convert(node, verbatim=verbatim)
            if item is not None:
                items.append(item)
        return items

    def is_blank_text(node: Any) -> bool:
        is_plain_string = isinstance(node, NavigableString) and not isinstance(
            node, (SoupComment, SoupDoctype)
        )
        return is_plain_string and not str(node).strip()

    def unwrap_implicit(items: list[HtmlItem]) -> list[HtmlItem]:
        """Drop <html>/<head>/<body> that the parser invented.

        lxml and html5lib wrap a fragment in a document skeleton, which would
        turn a parse-edit-render round trip into a rewrite. Wrappers the
        source actually asked for are kept.
        """
        unwrapped = []
        for item in items:
            if isinstance(item, Tag) and item.tag in DOCUMENT_ELEMENTS:
                unwrapped.extend(unwrap_implicit(item.children))
            else:
                unwrapped.append(item)
        return unwrapped

    soup = BeautifulSoup(html, parser or best_parser())
    roots = convert_children(soup.contents)
    while pending:
        soup_node, item, verbatim = pending.pop()
        # Verbatim is inherited: whitespace is significant in the whole
        # subtree of a <pre>, including inside the spans a syntax
        # highlighter wraps around each line, not just its direct children.
        item.children = convert_children(
            soup_node.contents, verbatim=verbatim or soup_node.name in PRE_ELEMENTS
        )
    if re.search(r"<\s*(html|head|body)\b", html, re.IGNORECASE):
        return roots
    return unwrap_implicit(roots)


def render_attrs(attrs: dict[str, Any]) -> str:
    """Render an attribute dict, leading space included, or ``""`` if empty."""
    parts = []
    for raw_name, value in attrs.items():
        if value is False or value is None:
            continue
        name = normalize_attr(raw_name)
        if not ATTR_NAME_RE.match(name):
            # Values are escaped below; names cannot be, so a quote or space
            # here would inject a second attribute into the rendered output.
            raise ValueError(f"invalid attribute name: {name!r}")
        if value is True:
            parts.append(name)
            continue
        if name in ("class", "style"):
            value = render_class(value) if name == "class" else render_style(value)
            # An all-false mapping means "no classes", so drop the attribute
            # rather than emitting class="", the way False drops one outright.
            if not value:
                continue
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


def render_style(value: Any) -> str:
    """Accept a string or a {property: value} mapping for ``style``.

    Property names are normalized too, so ``{"font_size": "2rem"}`` becomes
    ``font-size: 2rem``.
    """
    if not isinstance(value, dict):
        return str(value)
    return "; ".join(
        f"{normalize_attr(name)}: {item}"
        for name, item in value.items()
        if item is not None and item is not False
    )


def tag_class(tag: str, *, name: str | None = None) -> type[Tag]:
    """Build a Tag subclass bound to one tag name, so ``Div(...)`` works.

    Defined as a subclass with a fixed ``__init__`` rather than a Pydantic
    field override, which v2 rejects on non-annotated attributes. The result
    is registered in TAG_CLASSES, so parsing knows about custom tags too.
    """
    name = name or tag.replace("-", "_").title().replace("_", "")

    def __init__(self, *children: Any, **attrs: Any) -> None:
        if is_field_payload(children, attrs=attrs):
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
        return str(self)


class Comment(HtmlItem):
    """An HTML comment.

    Comment text has three syntax rules, each neutralized on render rather
    than escaped, since a comment is not an escaping context: it must not
    contain ``--`` (would end the comment early), must not start with ``>``
    or ``->`` (HTML5 reads ``<!-->`` and ``<!--->`` as complete comments, so
    the rest would parse as live markup), and must not end with ``-``.
    """

    type: Literal["comment"] = "comment"
    content: str

    def __str__(self) -> str:
        content = self.content.replace("--", "- -")
        if content.startswith((">", "->")):
            content = " " + content
        if content.endswith("-"):
            content += " "
        return marker()(f"<!--{content}-->")


class Doctype(HtmlItem):
    """A document type declaration. Defaults to the HTML5 doctype.

    ``content`` is what follows ``<!DOCTYPE`` — ``html`` for every modern
    document, or a legacy public/system identifier string when parsing old
    markup. A ``>`` in the content would end the declaration early and leak
    the rest into the document, so rendering refuses it.
    """

    type: Literal["doctype"] = "doctype"
    content: str = "html"

    def __str__(self) -> str:
        if ">" in self.content:
            raise ValueError(
                "doctype content cannot contain '>'; it would end the declaration"
            )
        return marker()(f"<!DOCTYPE {self.content}>")


class Raw(HtmlItem):
    """Pre-trusted markup, passed through unescaped.

    Never build this from user input.
    """

    type: Literal["raw"] = "raw"
    content: str

    def __str__(self) -> str:
        return marker()(self.content)


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

    def __init__(
        self, _tag: str | None = None, /, *children: Any, **attrs: Any
    ) -> None:
        # _tag is positional-only and children are variadic, so everything a
        # caller names is an attribute. That frees every possible attribute
        # name, including "tag", and makes the rule enforced by the signature
        # rather than by convention.
        if _tag is None:
            # Pydantic re-validation reaches here with fields as keywords;
            # a caller who passed an element name is always building markup,
            # even if the attributes happen to be named "tag" and "attrs".
            if is_field_payload(children, attrs=attrs):
                super().__init__(**attrs)
                return
            raise TypeError(
                "Tag() needs an element name as its first positional argument, "
                "as in Tag('div', ...)"
            )
        items = list(iter_children(children))
        if items and _tag in VOID_ELEMENTS:
            # Rendering would drop them silently, which hides the mistake.
            raise ValueError(f"<{_tag}> is a void element and cannot have children")
        super().__init__(
            tag=_tag,
            children=items,
            attrs={normalize_attr(key): value for key, value in attrs.items()},
        )

    @property
    def is_raw_text(self) -> bool:
        return self.tag in RAW_TEXT_ELEMENTS

    @property
    def is_void(self) -> bool:
        return self.tag in VOID_ELEMENTS

    @property
    def text(self) -> str:
        """All text in this subtree, unescaped."""
        return "".join(item.content for item in self.walk() if isinstance(item, Text))

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> Tag:
        """Validate, restoring the element class named by ``tag``.

        Children go through as_html_item, but the root is built by whichever
        class was asked, so ``Tag.model_validate`` would flatten a Div into a
        plain Tag without this.
        """
        if cls is Tag and isinstance(obj, dict):
            target = TAG_CLASSES.get(obj.get("tag"))
            if target is not None:
                return target.model_validate(obj, **kwargs)
        return super().model_validate(obj, **kwargs)

    @classmethod
    def model_validate_json(cls, json_data: str | bytes, **kwargs: Any) -> Tag:
        """Parse JSON, restoring the element class named by ``tag``."""
        if cls is Tag:
            return cls.model_validate(json.loads(json_data), **kwargs)
        return super().model_validate_json(json_data, **kwargs)

    def find(self, tag: str | None = None, **attrs: Any) -> Tag | None:
        """The first descendant tag matching, or None.

        Stops at the first hit rather than walking the whole tree.
        """
        return next(self.iter_find(tag, **attrs), None)

    def find_all(self, tag: str | None = None, **attrs: Any) -> list[Tag]:
        """Every descendant tag matching a name and/or attributes.

        Attribute names take the same Python spelling as the constructor::

            doc.find_all("a", class_="external")
        """
        return list(self.iter_find(tag, **attrs))

    def iter_find(self, tag: str | None = None, **attrs: Any) -> Iterator[Tag]:
        """find_all() as a lazy iterator."""
        wanted = {normalize_attr(key): value for key, value in attrs.items()}
        for item in self.walk():
            if (
                isinstance(item, Tag)
                and item is not self
                and (tag is None or item.tag == tag)
                and all(item.attrs.get(key) == value for key, value in wanted.items())
            ):
                yield item

    def walk(self) -> Iterator[HtmlItem]:
        """Yield this item, then every descendant, depth first.

        Iterative, so tree depth is not bounded by the Python stack.
        """
        stack: list[HtmlItem] = [self]
        while stack:
            item = stack.pop()
            yield item
            if isinstance(item, Tag):
                stack.extend(reversed(item.children))

    def __call__(self, *children: Any) -> Tag:
        """Return a copy with more children, for building in stages."""
        clone = self.model_copy()
        # model_copy is shallow: without these, the clone would share the
        # original's containers, and mutating one would mutate the other.
        clone.attrs = dict(self.attrs)
        clone.children = [*self.children, *iter_children(children)]
        return clone

    def __str__(self) -> str:
        # An explicit stack rather than recursion, so rendering neither
        # overflows on deep trees nor rebuilds every subtree string at every
        # level. Entries are either items to render or already-final strings
        # (closing tags).
        parts: list[str] = []
        stack: list[Any] = [self]
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                parts.append(node)
            elif isinstance(node, Tag) and type(node).__str__ is Tag.__str__:
                attrs = render_attrs(node.attrs)
                if node.is_void:
                    parts.append(f"<{node.tag}{attrs} />")
                elif node.is_raw_text:
                    parts.append(
                        f"<{node.tag}{attrs}>{node.render_raw_text()}</{node.tag}>"
                    )
                else:
                    parts.append(f"<{node.tag}{attrs}>")
                    stack.append(f"</{node.tag}>")
                    stack.extend(reversed(node.children))
            else:
                # A leaf, or a subclass with its own __str__ to honor.
                parts.append(str(node))
        return marker()("".join(parts))

    def render_raw_text(self) -> str:
        """Render <script>/<style> content without HTML-escaping it.

        Nothing can escape a raw text element except its own closing tag, so
        a child containing one would break out and, for a <script>, run as
        markup. That is refused rather than mangled.
        """
        content = "".join(
            child.content if isinstance(child, (Text, Raw)) else str(child)
            for child in self.children
        )
        if f"</{self.tag}" in content.lower():
            raise ValueError(
                f"<{self.tag}> content cannot contain '</{self.tag}'; "
                f"it would end the element"
            )
        return content


class Text(HtmlItem):
    """A run of text. Escaped on render."""

    type: Literal["text"] = "text"
    content: str

    def __str__(self) -> str:
        return marker()(escape(self.content))


ITEM_CLASSES.update(
    {"comment": Comment, "doctype": Doctype, "raw": Raw, "tag": Tag, "text": Text}
)

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
    "del",
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
    "selectedcontent",
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
    # Custom elements registered later get no MDN link; these are standard.
    _cls.__doc__ = (
        f"The HTML <{_tag}> element.\n\n"
        f"https://developer.mozilla.org/en-US/docs/Web/HTML/Element/{_tag}"
    )
    globals()[_cls.__name__] = _cls
    __all__.append(_cls.__name__)

del _tag, _cls

#: The elements this module generates, as opposed to any registered later by
#: tag_class(). TAG_CLASSES grows at runtime; this does not.
BUILTIN_TAGS = frozenset(_TAGS)
