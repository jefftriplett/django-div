"""Every generated tag renders, and behaves per its HTML category.

These are parametrized over TAG_CLASSES, so a tag added without the right
behavior fails here rather than in whatever page first used it.
"""

import pytest

import django_div
from django_div import (
    BUILTIN_TAGS,
    DEPRECATED_ELEMENTS,
    EXPERIMENTAL_ELEMENTS,
    PRE_ELEMENTS,
    RAW_TEXT_ELEMENTS,
    TAG_CLASSES,
    VOID_ELEMENTS,
    DeprecatedElementWarning,
    ExperimentalElementWarning,
    Tag,
    from_html,
    parse,
)
from tests import compat

# The suite turns DeprecationWarning into an error (see pyproject.toml), which
# is what should happen when application code reaches for <marquee>. Here the
# deprecated elements are the subject, so building one is not a mistake.
pytestmark = pytest.mark.filterwarnings("ignore::django_div.DeprecatedElementWarning")

#: Every current element in the HTML living standard, straight from the
#: browser-compat-data snapshot rather than transcribed, so a missing one is
#: a failure rather than a discovery.
HTML_ELEMENTS = compat.CURRENT

TAGS = sorted(BUILTIN_TAGS)
NORMAL_TAGS = [t for t in TAGS if t not in VOID_ELEMENTS and t not in RAW_TEXT_ELEMENTS]


# --- coverage of the standard -----------------------------------------------


def test_every_element_mdn_tracks_has_a_class():
    assert not compat.ELEMENTS - BUILTIN_TAGS, f"missing since {compat.SOURCE}"


def test_no_unknown_tags_are_generated():
    # BUILTIN_TAGS, not TAG_CLASSES: the registry also holds anything a
    # caller registered with tag_class(), which is not ours to police.
    assert not BUILTIN_TAGS - compat.ELEMENTS, f"unknown to {compat.SOURCE}"


def test_status_sets_match_mdn():
    """The library cannot read a fixture at runtime, so it keeps its own copy.

    Refreshing the snapshot with `just compat` fails here when a browser
    retires something, which is the moment to add or reclassify a class.
    """
    assert DEPRECATED_ELEMENTS == compat.DEPRECATED
    assert EXPERIMENTAL_ELEMENTS == compat.EXPERIMENTAL


def test_elements_without_an_mdn_page_match_mdn():
    """A null mdn_url upstream is why a docstring carries no link."""
    assert django_div._UNDOCUMENTED == compat.UNDOCUMENTED


@pytest.mark.parametrize(
    "category",
    [
        VOID_ELEMENTS,
        RAW_TEXT_ELEMENTS,
        PRE_ELEMENTS,
        DEPRECATED_ELEMENTS,
        EXPERIMENTAL_ELEMENTS,
    ],
)
def test_categories_only_name_real_tags(category):
    assert not category - BUILTIN_TAGS


def test_status_sets_do_not_overlap():
    """A tag is current, retired, or provisional, never two of them."""
    assert not DEPRECATED_ELEMENTS & EXPERIMENTAL_ELEMENTS
    assert BUILTIN_TAGS == HTML_ELEMENTS | DEPRECATED_ELEMENTS | EXPERIMENTAL_ELEMENTS


# --- deprecated and experimental elements -----------------------------------


@pytest.mark.parametrize("tag", sorted(DEPRECATED_ELEMENTS))
def test_building_a_deprecated_element_warns(tag):
    with pytest.warns(DeprecatedElementWarning, match=f"<{tag}> is deprecated"):
        TAG_CLASSES[tag]()


@pytest.mark.parametrize("tag", sorted(EXPERIMENTAL_ELEMENTS))
def test_building_an_experimental_element_warns_when_asked(tag):
    with pytest.warns(ExperimentalElementWarning, match=f"<{tag}> is experimental"):
        TAG_CLASSES[tag]()


def test_experimental_elements_are_silent_by_default():
    """A real interpreter, since pytest installs its own warning filters.

    Checking this in-process would only prove the filter works once it is
    reinstalled by hand, which says nothing about what a user sees.
    """
    import subprocess
    import sys

    builds = "; ".join(
        f"django_div.{TAG_CLASSES[tag].__name__}()"
        for tag in sorted(EXPERIMENTAL_ELEMENTS)
    )
    result = subprocess.run(
        [sys.executable, "-c", f"import django_div; {builds}"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_a_caller_filter_still_reaches_experimental_elements():
    """The shipped filter is appended, so -W and filterwarnings win."""
    import subprocess
    import sys

    name = TAG_CLASSES[min(EXPERIMENTAL_ELEMENTS)].__name__
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            f"import django_div; django_div.{name}()",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ExperimentalElementWarning" in result.stderr


def test_deprecated_element_warning_is_a_deprecation_warning():
    """So the stock -W and pytest filters already reach it."""
    assert issubclass(DeprecatedElementWarning, DeprecationWarning)
    assert issubclass(ExperimentalElementWarning, FutureWarning)


@pytest.mark.parametrize("tag", sorted(HTML_ELEMENTS))
def test_current_elements_do_not_warn(tag):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        TAG_CLASSES[tag]()


@pytest.mark.parametrize("tag", sorted(DEPRECATED_ELEMENTS))
def test_parsing_a_deprecated_element_is_quiet(tag):
    """Parsing reports what a document holds; it is not a choice to warn at.

    It still comes back as the right class, so a parsed tree round trips as
    itself rather than degrading to a generic Tag.
    """
    import warnings

    html = f"<{tag} />" if tag in VOID_ELEMENTS else f"<{tag}></{tag}>"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        parsed = parse(html, parser="html.parser")
    assert isinstance(parsed[0], TAG_CLASSES[tag])


@pytest.mark.parametrize("tag", sorted(DEPRECATED_ELEMENTS))
def test_deserializing_a_deprecated_element_is_quiet(tag):
    """Same reasoning as parsing: the tree already exists."""
    import warnings

    dumped = TAG_CLASSES[tag](id="x").model_dump_json()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        restored = Tag.model_validate_json(dumped)
    assert isinstance(restored, TAG_CLASSES[tag])


# --- every tag, the basics --------------------------------------------------


@pytest.mark.parametrize("tag", TAGS)
def test_tag_is_exported(tag):
    cls = TAG_CLASSES[tag]
    assert cls.__name__ in django_div.__all__
    assert getattr(django_div, cls.__name__) is cls


@pytest.mark.parametrize("tag", TAGS)
def test_tag_renders_empty(tag):
    expected = f"<{tag} />" if tag in VOID_ELEMENTS else f"<{tag}></{tag}>"
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
    assert item.is_void is (tag in VOID_ELEMENTS)
    assert item.is_raw_text is (tag in RAW_TEXT_ELEMENTS)


# --- behavior by category ---------------------------------------------------


@pytest.mark.parametrize("tag", sorted(VOID_ELEMENTS))
def test_void_tags_self_close_and_refuse_children(tag):
    assert str(TAG_CLASSES[tag]()) == f"<{tag} />"
    with pytest.raises(ValueError, match="void element"):
        TAG_CLASSES[tag]("child")


@pytest.mark.parametrize("tag", sorted(RAW_TEXT_ELEMENTS))
def test_raw_text_tags_do_not_escape(tag):
    assert str(TAG_CLASSES[tag]("a < b & c")) == f"<{tag}>a < b & c</{tag}>"


@pytest.mark.parametrize("tag", sorted(RAW_TEXT_ELEMENTS))
def test_raw_text_tags_refuse_their_own_closing_tag(tag):
    with pytest.raises(ValueError, match="would end the element"):
        str(TAG_CLASSES[tag](f"</{tag}>"))


@pytest.mark.parametrize("tag", NORMAL_TAGS)
def test_normal_tags_escape_and_nest(tag):
    cls = TAG_CLASSES[tag]
    assert str(cls("a < b")) == f"<{tag}>a &lt; b</{tag}>"
    assert str(cls(cls())) == f"<{tag}><{tag}></{tag}></{tag}>"


@pytest.mark.parametrize("tag", sorted(PRE_ELEMENTS))
def test_pre_tags_keep_their_whitespace(tag):
    html = f"<{tag}>  a\n  b  </{tag}>"
    assert str(from_html(html, parser="html.parser")) == html


# --- round trips ------------------------------------------------------------


#: <plaintext> has no end tag: everything after it is text to the end of the
#: document, so no parser can hand it back as it was written. Kept for the
#: same reason it exists in the standard's obsolete list -- old documents.
UNPARSEABLE = {"plaintext"}


@pytest.mark.parametrize("tag", [t for t in TAGS if t not in UNPARSEABLE])
def test_tag_round_trips_through_parsing(tag):
    html = f"<{tag} />" if tag in VOID_ELEMENTS else f"<{tag}></{tag}>"
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
    item = cls("a", "b") if tag not in VOID_ELEMENTS else cls()
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


def test_documented_element_count_matches_reality():
    """The element-count claim in the docs and README tracks BUILTIN_TAGS."""
    import pathlib

    root = pathlib.Path(__file__).parent.parent
    claim = f"{len(BUILTIN_TAGS)} elements"
    for name in ("docs/reference.md", "docs/building.md", "README.md"):
        assert claim in (root / name).read_text(), name


def read_documented_elements():
    """The 'All elements' table in docs/reference.md, as {tag: (class, notes)}."""
    import pathlib
    import re

    root = pathlib.Path(__file__).parent.parent
    text = (root / "docs/reference.md").read_text()
    table = text.split("### All elements", 1)[1]
    rows = re.findall(r"^\| `(\w+)` \| `<(\w+)>` \|([^|]*)\|$", table, re.MULTILINE)
    return {tag: (cls, notes.strip()) for cls, tag, notes in rows}


def test_documented_element_table_lists_every_tag():
    """A new element fails here until docs/reference.md names it."""
    assert set(read_documented_elements()) == BUILTIN_TAGS


@pytest.mark.parametrize("tag", TAGS)
def test_documented_element_table_matches_class_and_category(tag):
    documented_class, notes = read_documented_elements()[tag]
    assert documented_class == TAG_CLASSES[tag].__name__
    expected = [
        label
        for label, members in (
            ("void", VOID_ELEMENTS),
            ("raw text", RAW_TEXT_ELEMENTS),
            ("pre", PRE_ELEMENTS),
            ("deprecated", DEPRECATED_ELEMENTS),
            ("experimental", EXPERIMENTAL_ELEMENTS),
        )
        if tag in members
    ]
    assert notes == ", ".join(expected)


@pytest.mark.parametrize("tag", TAGS)
def test_builtin_docstrings_link_to_mdn(tag):
    if tag in django_div._UNDOCUMENTED:
        pytest.skip("MDN has no page for this element yet")
    assert (
        f"developer.mozilla.org/en-US/docs/Web/HTML/Element/{tag}"
        in TAG_CLASSES[tag].__doc__
    )


@pytest.mark.parametrize("tag", sorted(DEPRECATED_ELEMENTS | EXPERIMENTAL_ELEMENTS))
def test_docstrings_say_which_elements_are_not_current(tag):
    doc = TAG_CLASSES[tag].__doc__
    expected = "Deprecated" if tag in DEPRECATED_ELEMENTS else "Experimental"
    assert expected in doc


def test_custom_elements_do_not_claim_mdn_pages():
    from django_div import tag_class

    cls = tag_class("not-a-real-element")
    assert "mozilla" not in (cls.__doc__ or "")
