"""Global attributes and input types, checked against the standard's lists.

Neither list lives in the library: attributes and ``type`` values are passed
through unvalidated, on purpose, so a Django project can use ``hx-get`` or a
``data-`` name nobody has standardized. What can still go wrong is the
translation layer -- a spelling ``normalize_attr()`` mangles, a name
``ATTR_NAME_RE`` rejects, a value the renderer or the parser loses. These
tests walk the real lists so that failure shows up here.

Both lists come from the browser-compat-data snapshot in ``tests/data``, so
they cannot drift out of a typo: a hand-written set that quietly covered 29
of 30 attributes would still pass everything below.
"""

import keyword

import pytest

from django_div import (
    ATTR_NAME_RE,
    Div,
    Input,
    Label,
    Link,
    Script,
    from_html,
    normalize_attr,
)
from tests import compat

#: Every global attribute and every ``<input type>`` value, from the
#: browser-compat-data snapshot. BCD's ``data_attributes`` entry stands for
#: the open-ended ``data-*`` family rather than a real name, and is dropped
#: when the snapshot is generated; it is covered separately below.
GLOBAL_ATTRIBUTES = compat.GLOBAL_ATTRIBUTES
ELEMENT_ATTRIBUTES = compat.ELEMENT_ATTRIBUTES
INPUT_TYPES = compat.INPUT_TYPES

ATTRIBUTES = sorted(GLOBAL_ATTRIBUTES)
EVERY_ATTRIBUTE = sorted(compat.ATTRIBUTES)
SVG_ATTRIBUTES = compat.SVG_ATTRIBUTES
TYPES = sorted(INPUT_TYPES)


def spelling(attribute: str) -> str:
    """The Python name for an HTML attribute: the inverse of normalize_attr.

    Hyphens become underscores, and a trailing underscore is the escape
    hatch for Python's keywords. That is the whole rule, and
    test_only_python_keywords_need_respelling pins down that it stays so.
    """
    name = attribute.replace("-", "_")
    return f"{name}_" if keyword.iskeyword(name) else name


# --- global attributes ------------------------------------------------------


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_has_a_python_spelling(attribute):
    assert normalize_attr(spelling(attribute)) == attribute


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_is_a_renderable_name(attribute):
    """Values are escaped on render; names cannot be, so they are validated."""
    assert ATTR_NAME_RE.match(attribute)


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_renders_with_a_value(attribute):
    rendered = str(Div(**{spelling(attribute): "v"}))
    assert rendered == f'<div {attribute}="v"></div>'


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_renders_bare_when_true(attribute):
    """``hidden``, ``inert``, and friends are boolean in HTML."""
    assert str(Div(**{spelling(attribute): True})) == f"<div {attribute}></div>"


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_drops_out_when_false_or_none(attribute):
    for value in (False, None):
        assert str(Div(**{spelling(attribute): value})) == "<div></div>"


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_round_trips_through_parsing(attribute):
    html = f'<div {attribute}="v"></div>'
    parsed = from_html(html, parser="html.parser")
    assert parsed.attrs[attribute] == "v"
    assert str(parsed) == html


@pytest.mark.parametrize("attribute", ATTRIBUTES)
def test_global_attribute_is_global(attribute):
    """Not special-cased to one element: every tag takes every one of them."""
    assert str(Input(**{spelling(attribute): "v"})) == f'<input {attribute}="v" />'


def test_only_python_keywords_need_a_trailing_underscore():
    """The seven names a user has to remember, across HTML and SVG.

    ``class`` and ``is`` are global; ``for`` is on label and output,
    ``async`` on script, ``as`` on link, and ``in`` and ``from`` come from
    SVG filters and ``<animate>``. A new attribute that collided with a
    Python keyword would land here, and that list would have grown.
    """
    assert {
        "as",
        "async",
        "class",
        "for",
        "from",
        "in",
        "is",
    } == compat.KEYWORD_ATTRIBUTES


def read_documented_keywords():
    """The 'Reserved words' table in docs/building.md, as {python: html}."""
    import pathlib
    import re

    page = (pathlib.Path(__file__).parent.parent / "docs/building.md").read_text()
    table = page.split("### Reserved words", 1)[1].split("###", 1)[0]
    return dict(re.findall(r"^\| `(\w+)_` \| `(\w+)` \|", table, re.MULTILINE))


def test_the_documented_reserved_words_are_exactly_the_real_ones():
    """The table in the docs is a promise; MDN decides whether it holds.

    A keyword attribute nobody wrote down is a user hitting a SyntaxError
    with no way to look up the fix, and a documented one that no longer
    exists is a lie. Refreshing the snapshot fails here on either.
    """
    documented = read_documented_keywords()
    assert set(documented.values()) == compat.KEYWORD_ATTRIBUTES
    for python_name, html_name in documented.items():
        assert normalize_attr(f"{python_name}_") == html_name


def test_soft_keywords_and_builtins_need_no_respelling():
    """``type``, ``min``, ``max``, ``open``: legal as keyword arguments.

    Only a hard keyword is a syntax error in an argument list, so shadowing
    a builtin inside a call costs nothing and needs no underscore.
    """
    for name in ("type", "min", "max", "open", "list", "id"):
        assert spelling(name) == name
        assert str(Div(**{name: "v"})) == f'<div {name}="v"></div>'


def test_no_attribute_name_contains_an_underscore():
    """So ``_`` -> ``-`` never has to make an exception.

    normalize_attr turns every underscore into a hyphen. That is only safe
    while no real attribute name has one in it, which is also what lets the
    snapshot tell an attribute from one of BCD's sub-feature keys.
    """
    assert not [a for a in compat.ATTRIBUTES if "_" in a]


@pytest.mark.parametrize(
    "python_name,html_name",
    [
        ("data_id", "data-id"),
        ("data_test_id", "data-test-id"),
        ("data_", "data"),
    ],
)
def test_data_attributes_reach_any_name(python_name, html_name):
    """BCD's ``data_attributes`` entry: the open-ended ``data-*`` family."""
    assert str(Div(**{python_name: "v"})) == f'<div {html_name}="v"></div>'


# --- every attribute, global or not -----------------------------------------


@pytest.mark.parametrize("attribute", EVERY_ATTRIBUTE)
def test_attribute_round_trips_through_its_python_spelling(attribute):
    """normalize_attr(spelling(x)) == x, for every attribute in HTML."""
    assert normalize_attr(spelling(attribute)) == attribute


@pytest.mark.parametrize("attribute", EVERY_ATTRIBUTE)
def test_attribute_is_a_renderable_name(attribute):
    assert ATTR_NAME_RE.match(attribute)


@pytest.mark.parametrize("attribute", EVERY_ATTRIBUTE)
def test_attribute_renders_with_a_value(attribute):
    assert str(Div(**{spelling(attribute): "v"})) == f'<div {attribute}="v"></div>'


@pytest.mark.parametrize("attribute", sorted(SVG_ATTRIBUTES))
def test_svg_attribute_is_reachable_as_a_keyword_argument(attribute):
    """Every SVG name is a Python identifier once hyphens become underscores.

    Which is worth knowing, because it means inline SVG never needs the
    dictionary escape hatch that a name like "hx-on:click" does.
    """
    assert spelling(attribute).isidentifier()
    assert str(Div(**{spelling(attribute): "v"})) == f'<div {attribute}="v"></div>'


@pytest.mark.parametrize("attribute", EVERY_ATTRIBUTE)
def test_attribute_round_trips_through_parsing(attribute):
    """Case-folded, because a parser lowercases every attribute name.

    HTML attribute names are ASCII case-insensitive, so a parser is entitled
    to hand back a name in a different case than the source wrote it. Only
    one name in the standard is spelled with a capital anywhere -- iframe's
    privateToken -- and it is the same attribute either way.
    """
    html = f'<div {attribute}="v"></div>'
    assert str(from_html(html, parser="html.parser")) == html.lower()


def test_attribute_names_keep_their_case_on_render():
    """Rendering is not parsing: what you write is what goes out.

    Nothing normalizes case on the way out, which matters for SVG and
    MathML, where viewBox and friends really are case-sensitive.
    """
    assert str(Div(viewBox="0 0 1 1")) == '<div viewBox="0 0 1 1"></div>'
    assert str(Div(privateToken="v")) == '<div privateToken="v"></div>'


@pytest.mark.parametrize(
    "python_name,html_name",
    [
        ("for_", "for"),
        ("async_", "async"),
        ("as_", "as"),
        ("class_", "class"),
        ("is_", "is"),
        ("http_equiv", "http-equiv"),
        ("accept_charset", "accept-charset"),
    ],
)
def test_the_awkward_spellings(python_name, html_name):
    """The names that cannot be written literally, spelled out once."""
    assert normalize_attr(python_name) == html_name
    assert str(Div(**{python_name: "v"})) == f'<div {html_name}="v"></div>'


def test_a_keyword_attribute_works_on_the_element_that_takes_it():
    from django_div import tag_class

    animate = tag_class("animate")
    assert str(animate(from_="0", to="1")) == '<animate from="0" to="1"></animate>'
    assert str(Label("Name", for_="n")) == '<label for="n">Name</label>'
    assert str(Script(src="/a.js", async_=True)) == (
        '<script src="/a.js" async></script>'
    )
    assert str(Link(rel="preload", as_="style")) == '<link rel="preload" as="style" />'


# --- input types ------------------------------------------------------------


@pytest.mark.parametrize("input_type", TYPES)
def test_input_type_renders(input_type):
    assert str(Input(type=input_type)) == f'<input type="{input_type}" />'


@pytest.mark.parametrize("input_type", TYPES)
def test_input_type_survives_as_a_value(input_type):
    """Values are not normalized, so ``datetime-local`` keeps its hyphen."""
    assert Input(type=input_type).attrs["type"] == input_type


@pytest.mark.parametrize("input_type", TYPES)
def test_input_type_round_trips_through_parsing(input_type):
    html = f'<input type="{input_type}" />'
    parsed = from_html(html, parser="html.parser")
    assert parsed.attrs["type"] == input_type
    assert str(parsed) == html


@pytest.mark.parametrize("input_type", TYPES)
def test_input_type_renders_alongside_the_usual_form_attributes(input_type):
    rendered = str(Input(type=input_type, name="field", required=True, class_="c"))
    assert rendered == f'<input type="{input_type}" name="field" required class="c" />'


def test_input_types_are_safe_as_attribute_values():
    """Nothing here needs escaping, so a new one that does is worth knowing."""
    for input_type in INPUT_TYPES:
        assert input_type == input_type.lower()
        assert not set(input_type) - set("abcdefghijklmnopqrstuvwxyz-")


def test_the_lists_are_not_empty():
    """A snapshot that failed to generate would make every test above vacuous."""
    assert len(GLOBAL_ATTRIBUTES) > 20
    assert len(INPUT_TYPES) > 20
