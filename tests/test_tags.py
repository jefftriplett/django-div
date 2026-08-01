"""Every generated tag renders, and behaves per its HTML category.

These are parametrized over TAG_CLASSES, so a tag added without the right
behavior fails here rather than in whatever page first used it.
"""

import pytest

import django_div
from django_div import (
    BUILTIN_TAGS,
    PRE_TAGS,
    RAW_TEXT_TAGS,
    TAG_CLASSES,
    VOID_TAGS,
    Tag,
    from_html,
    parse,
)

#: Every element in the HTML living standard, so a missing one is a failure
#: rather than a discovery. Obsolete elements are deliberately excluded.
HTML_ELEMENTS = set(
    [
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
)

#: Dropped from the standard but still found in the wild, so still parsed.
LEGACY_ELEMENTS = {"param"}

TAGS = sorted(BUILTIN_TAGS)
NORMAL_TAGS = [t for t in TAGS if t not in VOID_TAGS and t not in RAW_TEXT_TAGS]


# --- coverage of the standard -----------------------------------------------


def test_every_html_element_has_a_class():
    assert not HTML_ELEMENTS - BUILTIN_TAGS


def test_no_unknown_tags_are_generated():
    # BUILTIN_TAGS, not TAG_CLASSES: the registry also holds anything a
    # caller registered with tag_class(), which is not ours to police.
    assert not BUILTIN_TAGS - HTML_ELEMENTS - LEGACY_ELEMENTS


@pytest.mark.parametrize("category", [VOID_TAGS, RAW_TEXT_TAGS, PRE_TAGS])
def test_categories_only_name_real_tags(category):
    assert not category - BUILTIN_TAGS


# --- every tag, the basics --------------------------------------------------


@pytest.mark.parametrize("tag", TAGS)
def test_tag_is_exported(tag):
    cls = TAG_CLASSES[tag]
    assert cls.__name__ in django_div.__all__
    assert getattr(django_div, cls.__name__) is cls


@pytest.mark.parametrize("tag", TAGS)
def test_tag_renders_empty(tag):
    expected = f"<{tag} />" if tag in VOID_TAGS else f"<{tag}></{tag}>"
    assert str(TAG_CLASSES[tag]()) == expected


@pytest.mark.parametrize("tag", TAGS)
def test_tag_renders_attributes(tag):
    rendered = str(TAG_CLASSES[tag](id="x", class_="y", data_n="1"))
    assert rendered.startswith(f'<{tag} id="x" class="y" data-n="1"')


@pytest.mark.parametrize("tag", TAGS)
def test_tag_knows_its_own_name(tag):
    assert TAG_CLASSES[tag]().tag == tag


@pytest.mark.parametrize("tag", TAGS)
def test_tag_reports_its_categories(tag):
    item = TAG_CLASSES[tag]()
    assert item.is_void is (tag in VOID_TAGS)
    assert item.is_raw_text is (tag in RAW_TEXT_TAGS)


# --- behavior by category ---------------------------------------------------


@pytest.mark.parametrize("tag", sorted(VOID_TAGS))
def test_void_tags_self_close_and_refuse_children(tag):
    assert str(TAG_CLASSES[tag]()) == f"<{tag} />"
    with pytest.raises(ValueError, match="void element"):
        TAG_CLASSES[tag]("child")


@pytest.mark.parametrize("tag", sorted(RAW_TEXT_TAGS))
def test_raw_text_tags_do_not_escape(tag):
    assert str(TAG_CLASSES[tag]("a < b & c")) == f"<{tag}>a < b & c</{tag}>"


@pytest.mark.parametrize("tag", sorted(RAW_TEXT_TAGS))
def test_raw_text_tags_refuse_their_own_closing_tag(tag):
    with pytest.raises(ValueError, match="would end the element"):
        str(TAG_CLASSES[tag](f"</{tag}>"))


@pytest.mark.parametrize("tag", NORMAL_TAGS)
def test_normal_tags_escape_and_nest(tag):
    cls = TAG_CLASSES[tag]
    assert str(cls("a < b")) == f"<{tag}>a &lt; b</{tag}>"
    assert str(cls(cls())) == f"<{tag}><{tag}></{tag}></{tag}>"


@pytest.mark.parametrize("tag", sorted(PRE_TAGS))
def test_pre_tags_keep_their_whitespace(tag):
    html = f"<{tag}>  a\n  b  </{tag}>"
    assert str(from_html(html, parser="html.parser")) == html


# --- round trips ------------------------------------------------------------


@pytest.mark.parametrize("tag", TAGS)
def test_tag_round_trips_through_parsing(tag):
    html = f"<{tag} />" if tag in VOID_TAGS else f"<{tag}></{tag}>"
    # html.parser leaves the fragment alone; lxml would move a stray <td>
    # into a table, which is correct for a document but not a round trip.
    parsed = parse(html, parser="html.parser")
    assert len(parsed) == 1
    assert isinstance(parsed[0], TAG_CLASSES[tag])
    assert str(parsed[0]) == html


@pytest.mark.parametrize("tag", TAGS)
def test_tag_round_trips_through_json(tag):
    item = TAG_CLASSES[tag](id="x")
    restored = Tag.model_validate_json(item.model_dump_json())
    assert isinstance(restored, TAG_CLASSES[tag])
    assert str(restored) == str(item)


# --- constructor shape ------------------------------------------------------


@pytest.mark.parametrize("tag", TAGS)
def test_tag_constructor_takes_children_positionally_and_attrs_by_keyword(tag):
    """Children are variadic positional; everything named is an attribute.

    Python guarantees that anything after *children is keyword-only, so this
    checks the signature has not grown a plain positional parameter that
    would quietly accept an attribute by position.
    """
    import inspect

    kinds = [
        parameter.kind
        for name, parameter in inspect.signature(
            TAG_CLASSES[tag].__init__
        ).parameters.items()
        if name != "self"
    ]
    assert kinds == [
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    ]


@pytest.mark.parametrize("tag", TAGS)
def test_attributes_cannot_be_passed_positionally(tag):
    cls = TAG_CLASSES[tag]
    # A second positional is another child, never an attribute value.
    item = cls("a", "b") if tag not in VOID_TAGS else cls()
    assert item.attrs == {}


def test_generic_tag_name_is_positional_only():
    """So that "tag" stays usable as an attribute name."""
    import inspect

    parameters = inspect.signature(Tag.__init__).parameters
    assert parameters["_tag"].kind is inspect.Parameter.POSITIONAL_ONLY

    with pytest.raises(TypeError):
        Tag(_tag="div")


def test_tag_named_attribute_is_not_swallowed():
    assert str(Tag("div", tag="value")) == '<div tag="value"></div>'


def test_generic_tag_without_a_name_says_so():
    with pytest.raises(TypeError, match="first positional argument"):
        Tag()


@pytest.mark.parametrize("tag", NORMAL_TAGS)
def test_element_siblings_and_attributes_together(tag):
    """Div(Div(), Div(), class_="md") and friends.

    Children keep being positional however many there are, and attributes
    stay keyword, so the two never compete for a slot.
    """
    cls = TAG_CLASSES[tag]
    assert str(cls(cls(), cls(), class_="md")) == (
        f'<{tag} class="md"><{tag}></{tag}><{tag}></{tag}></{tag}>'
    )


@pytest.mark.parametrize("tag", NORMAL_TAGS)
def test_mixed_children_and_several_attributes(tag):
    cls = TAG_CLASSES[tag]
    assert str(cls(cls("a"), "tail", class_="md", id="x")) == (
        f'<{tag} class="md" id="x"><{tag}>a</{tag}>tail</{tag}>'
    )
