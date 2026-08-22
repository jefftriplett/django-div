"""Global attributes and input types, checked against the standard's lists.

Neither list lives in the library: attributes and ``type`` values are passed
through unvalidated, on purpose, so a Django project can use ``hx-get`` or a
``data-`` name nobody has standardized. What can still go wrong is the
translation layer -- a spelling ``normalize_attr()`` mangles, a name
``ATTR_NAME_RE`` rejects, a value the renderer or the parser loses. These
tests walk the real lists so that failure shows up here.

Both sets are transcribed from mdn/browser-compat-data:
``html/global_attributes.json`` and ``html/elements/input/``.
"""

import keyword

import pytest

from django_div import ATTR_NAME_RE, Div, Input, from_html, normalize_attr

#: Every global attribute, by its HTML spelling. BCD's ``data_attributes``
#: entry stands for the open-ended ``data-*`` family rather than a real
#: attribute name, so it is covered separately below.
GLOBAL_ATTRIBUTES = {
    "accesskey",
    "anchor",
    "autocapitalize",
    "autocorrect",
    "autofocus",
    "class",
    "contenteditable",
    "dir",
    "draggable",
    "enterkeyhint",
    "exportparts",
    "headingoffset",
    "headingreset",
    "hidden",
    "id",
    "inert",
    "inputmode",
    "is",
    "lang",
    "nonce",
    "part",
    "popover",
    "slot",
    "spellcheck",
    "style",
    "tabindex",
    "title",
    "translate",
    "virtualkeyboardpolicy",
    "writingsuggestions",
}

#: Every ``<input type>`` value in the standard. All 22 are current; the
#: standard has no deprecated ones left, ``datetime`` having been dropped
#: outright rather than kept around.
INPUT_TYPES = {
    "button",
    "checkbox",
    "color",
    "date",
    "datetime-local",
    "email",
    "file",
    "hidden",
    "image",
    "month",
    "number",
    "password",
    "radio",
    "range",
    "reset",
    "search",
    "submit",
    "tel",
    "text",
    "time",
    "url",
    "week",
}

ATTRIBUTES = sorted(GLOBAL_ATTRIBUTES)
TYPES = sorted(INPUT_TYPES)


def spelling(attribute: str) -> str:
    """The Python keyword name for an HTML attribute.

    A trailing underscore is the escape hatch for Python's keywords, and
    nothing else about a global attribute needs respelling, so this is the
    whole rule. test_only_python_keywords_need_respelling pins that down.
    """
    return f"{attribute}_" if keyword.iskeyword(attribute) else attribute


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


def test_only_python_keywords_need_respelling():
    """Which is why ``normalize_attr`` drops one trailing underscore.

    A new global attribute that collided with a Python keyword would land
    here, and the list of names a user has to remember would have grown.
    """
    respelled = {a for a in GLOBAL_ATTRIBUTES if spelling(a) != a}
    assert respelled == {"class", "is"}


def test_no_global_attribute_name_contains_an_underscore():
    """So ``_`` -> ``-`` never has to make an exception.

    normalize_attr turns every underscore into a hyphen. That is only safe
    while no real attribute name has one in it.
    """
    assert not [a for a in GLOBAL_ATTRIBUTES if "_" in a]


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
    """Nothing here needs escaping, so a mismatch means a typo in the list."""
    for input_type in INPUT_TYPES:
        assert input_type == input_type.lower()
        assert not set(input_type) - set("abcdefghijklmnopqrstuvwxyz-")
