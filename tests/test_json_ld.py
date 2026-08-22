"""json_ld(), and the escaping that keeps a payload from becoming markup.

A <script> is raw text: the parser reads it until it sees the closing tag and
does not decode entities on the way. So the usual escaping is not available,
and the only way to embed arbitrary JSON safely is to spell the dangerous
characters as the \\uXXXX escapes JSON already understands. These tests cover
that the data survives that rewriting unchanged, which is the whole trick.
"""

import json

import pytest
from pydantic import BaseModel, ConfigDict, Field

from django_div import Div, Script, as_json, from_html, json_ld


class Person(BaseModel):
    """A schema.org Person, the way JSON-LD needs it spelled."""

    model_config = ConfigDict(populate_by_name=True)

    context: str = Field("https://schema.org", alias="@context")
    type: str = Field("Person", alias="@type")
    name: str
    url: str | None = None
    email: str | None = None


def payload(tag):
    """The JSON out of a rendered <script>, parsed back."""
    rendered = str(tag)
    return json.loads(rendered.split(">", 1)[1].rsplit("<", 1)[0])


# --- shape ------------------------------------------------------------------


def test_renders_a_script_tag_with_the_ld_json_type():
    assert str(json_ld({"a": 1})) == (
        '<script type="application/ld+json">{"a":1}</script>'
    )


def test_returns_a_real_script_element():
    """So it nests, walks, and round trips like anything else in a tree."""
    tag = json_ld({"a": 1})
    assert isinstance(tag, Script)
    assert tag.tag == "script"
    assert tag.is_raw_text


def test_nests_in_a_document():
    head = Div(json_ld({"a": 1}))
    assert str(head).startswith('<div><script type="application/ld+json">')


def test_extra_keywords_become_attributes():
    assert str(json_ld({"a": 1}, id="graph")).startswith(
        '<script type="application/ld+json" id="graph">'
    )


def test_the_type_can_be_overridden():
    assert str(json_ld({"a": 1}, type="application/json")).startswith(
        '<script type="application/json">'
    )


# --- pydantic ---------------------------------------------------------------


def test_a_model_renders_by_its_aliases():
    """@context and @type are not Python names, so they can only be aliases."""
    assert payload(json_ld(Person(name="Ada Lovelace"))) == {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Ada Lovelace",
    }


def test_none_fields_are_dropped():
    """A JSON-LD null is not a value, so writing one only adds bytes."""
    assert "url" not in payload(json_ld(Person(name="Ada")))
    assert payload(json_ld(Person(name="Ada", url="/ada")))["url"] == "/ada"


def test_a_list_of_models_renders_as_an_array():
    data = payload(json_ld([Person(name="Ada"), Person(name="Grace")]))
    assert [item["name"] for item in data] == ["Ada", "Grace"]


def test_a_nested_model_is_reached():
    class Article(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        type: str = Field("Article", alias="@type")
        author: Person

    data = payload(json_ld(Article(author=Person(name="Ada"))))
    assert data["author"]["@type"] == "Person"


def test_json_types_are_coerced():
    """mode="json", so a datetime is a string rather than a TypeError."""
    import datetime

    class Event(BaseModel):
        start: datetime.datetime

    data = payload(json_ld(Event(start=datetime.datetime(2026, 8, 22, 9, 30))))
    assert data["start"].startswith("2026-08-22T09:30")


def test_as_json_refuses_what_it_cannot_serialize():
    with pytest.raises(TypeError, match="cannot serialize object as JSON"):
        as_json(object())


# --- escaping ---------------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "</script>",
        "</SCRIPT >",
        "</script><img src=x onerror=alert(1)>",
        "<!--",
        "<!-- <script>",
        "a & b",
        "\u2028",
        "\u2029",
    ],
)
def test_hostile_content_cannot_escape_the_script(hostile):
    rendered = str(json_ld({"name": hostile}))
    body = rendered.split(">", 1)[1].rsplit("<", 1)[0]
    for character in "<>&\u2028\u2029":
        assert character not in body


@pytest.mark.parametrize(
    "hostile",
    [
        "</script>",
        "</script><img src=x onerror=alert(1)>",
        "<!--",
        "a & b < c > d",
        "line\u2028break",
    ],
)
def test_escaping_does_not_change_the_data(hostile):
    """The escapes are a spelling, not a transformation: json.loads undoes them."""
    assert payload(json_ld({"name": hostile}))["name"] == hostile


def test_a_key_is_escaped_too_not_just_a_value():
    assert payload(json_ld({"</script>": 1})) == {"</script>": 1}


def test_the_rendered_tag_is_a_single_element():
    """The proof that matters: a parser sees one script and nothing else."""
    hostile = "</script><img src=x onerror=alert(1)>"
    parsed = from_html(str(json_ld({"name": hostile})), parser="html.parser")
    assert isinstance(parsed, Script)
    assert parsed.find("img") is None
    assert json.loads(parsed.text)["name"] == hostile


def test_raw_script_content_would_have_raised_instead():
    """Which is why json_ld exists: the safe path is not the obvious one.

    Handing the same JSON to Script() refuses to render rather than
    injecting, so nothing here is a live vulnerability -- but refusing to
    render a legitimate product description is not a usable answer either.
    """
    unescaped = json.dumps({"name": "</script>"})
    with pytest.raises(ValueError, match="would end the element"):
        str(Script(unescaped))


# --- round trips ------------------------------------------------------------


def test_survives_a_json_round_trip_of_the_tree():
    tag = json_ld(Person(name="Ada"))
    restored = Script.model_validate_json(tag.model_dump_json())
    assert str(restored) == str(tag)


def test_parses_back_and_still_renders_identically():
    tag = json_ld(Person(name="Ada", email="ada@example.com"))
    parsed = from_html(str(tag), parser="html.parser")
    assert str(parsed) == str(tag)
    assert json.loads(parsed.text)["email"] == "ada@example.com"


def test_non_ascii_is_not_mangled():
    """ensure_ascii is off, so UTF-8 goes out as itself and stays shorter."""
    tag = json_ld({"name": "Ada Lovelace — 日本語"})
    assert "日本語" in str(tag)
    assert payload(tag)["name"] == "Ada Lovelace — 日本語"
