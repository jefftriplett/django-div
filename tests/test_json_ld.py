"""JsonLd, and the escaping that keeps a payload from becoming markup.

A <script> is raw text: the parser reads it until it sees the closing tag and
does not decode entities on the way. So the usual escaping is not available,
and the only way to embed arbitrary JSON safely is to spell the dangerous
characters as the \\uXXXX escapes JSON already understands. These tests cover
that the data survives that rewriting unchanged, which is the whole trick.
"""

import json

import pytest
from pydantic import BaseModel, ConfigDict, Field

from django_div import Div, JsonLd, Script, as_json, from_html, render_json_ld


class Person(BaseModel):
    """A schema.org Person, spelled the way JSON-LD needs.

    Nothing here comes from django_div: "@context" and "@type" are not
    Python names, so they are declared as aliases, which is all JsonLd
    needs from a model.
    """

    model_config = ConfigDict(populate_by_name=True)

    context: str = Field("https://schema.org", alias="@context")
    type: str = Field("Person", alias="@type")
    name: str
    url: str | None = None
    email: str | None = None
    same_as: list[str] | None = Field(None, alias="sameAs")


def payload(tag):
    """The JSON out of a rendered <script>, parsed back."""
    rendered = str(tag)
    return json.loads(rendered.split(">", 1)[1].rsplit("<", 1)[0])


# --- shape ------------------------------------------------------------------


def test_renders_a_script_tag_with_the_ld_json_type():
    assert str(JsonLd({"a": 1})) == (
        '<script type="application/ld+json">{"a":1}</script>'
    )


def test_returns_a_real_script_element():
    """So it nests, walks, and round trips like anything else in a tree."""
    tag = JsonLd({"a": 1})
    assert isinstance(tag, Script)
    assert tag.tag == "script"
    assert tag.is_raw_text


def test_nests_in_a_document():
    head = Div(JsonLd({"a": 1}))
    assert str(head).startswith('<div><script type="application/ld+json">')


def test_extra_keywords_become_attributes():
    assert str(JsonLd({"a": 1}, id="graph")).startswith(
        '<script type="application/ld+json" id="graph">'
    )


def test_the_type_can_be_overridden():
    assert str(JsonLd({"a": 1}, type="application/json")).startswith(
        '<script type="application/json">'
    )


# --- pydantic ---------------------------------------------------------------


def test_a_model_renders_by_its_aliases():
    """by_alias, so a field aliased to "@type" arrives spelled that way."""
    assert payload(JsonLd(Person(name="Ada Lovelace"))) == {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Ada Lovelace",
    }


def test_none_fields_are_dropped():
    """A JSON-LD null is not a value, so writing one only adds bytes."""
    assert "url" not in payload(JsonLd(Person(name="Ada")))
    assert payload(JsonLd(Person(name="Ada", url="/ada")))["url"] == "/ada"


def test_any_model_works_no_base_class_required():
    """Nothing has to inherit from anything in django_div."""

    class Bare(BaseModel):
        name: str

    assert payload(JsonLd(Bare(name="Ada"))) == {"name": "Ada"}


def test_a_list_of_models_renders_as_an_array():
    data = payload(JsonLd([Person(name="Ada"), Person(name="Grace")]))
    assert [item["name"] for item in data] == ["Ada", "Grace"]


def test_a_nested_model_is_reached():
    class Article(BaseModel):
        type: str = Field("Article", alias="@type")
        author: Person

    data = payload(JsonLd(Article(author=Person(name="Ada"))))
    assert data["author"]["@type"] == "Person"


def test_json_types_are_coerced():
    """mode="json", so a datetime is a string rather than a TypeError."""
    import datetime

    class Event(BaseModel):
        start: datetime.datetime

    data = payload(JsonLd(Event(start=datetime.datetime(2026, 8, 22, 9, 30))))
    assert data["start"].startswith("2026-08-22T09:30")


def test_a_dict_is_the_escape_hatch_for_other_dump_options():
    """Models are dumped by alias with nulls dropped, which JSON-LD wants.

    A caller who wants something else dumps the model themselves and hands
    over the result, so the opinion is never in the way.
    """
    person = Person(name="Ada")
    data = payload(JsonLd(person.model_dump(by_alias=True)))
    assert data["url"] is None


def test_as_json_refuses_what_it_cannot_serialize():
    with pytest.raises(TypeError, match="cannot serialize object as JSON"):
        as_json(object())


# --- render_json_ld ---------------------------------------------------------


def test_render_json_ld_is_the_serializer_on_its_own():
    """Usable without a tag, for an attribute or another transport."""
    assert render_json_ld({"a": 1}) == '{"a":1}'
    assert render_json_ld({"a": "</script>"}) == '{"a":"\\u003c/script\\u003e"}'


def test_render_json_ld_is_compact():
    """It is markup, so the whitespace is not worth the bytes."""
    assert render_json_ld({"a": 1, "b": [1, 2]}) == '{"a":1,"b":[1,2]}'


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
    rendered = str(JsonLd({"name": hostile}))
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
    assert payload(JsonLd({"name": hostile}))["name"] == hostile


def test_a_key_is_escaped_too_not_just_a_value():
    assert payload(JsonLd({"</script>": 1})) == {"</script>": 1}


def test_the_rendered_tag_is_a_single_element():
    """The proof that matters: a parser sees one script and nothing else."""
    hostile = "</script><img src=x onerror=alert(1)>"
    parsed = from_html(str(JsonLd({"name": hostile})), parser="html.parser")
    assert isinstance(parsed, Script)
    assert parsed.find("img") is None
    assert json.loads(parsed.text)["name"] == hostile


def test_raw_script_content_would_have_raised_instead():
    """Which is why JsonLd exists: the safe path is not the obvious one.

    Handing the same JSON to Script() refuses to render rather than
    injecting, so nothing here is a live vulnerability -- but refusing to
    render a legitimate product description is not a usable answer either.
    """
    unescaped = json.dumps({"name": "</script>"})
    with pytest.raises(ValueError, match="would end the element"):
        str(Script(unescaped))


# --- round trips ------------------------------------------------------------


def test_survives_a_json_round_trip_of_the_tree():
    tag = JsonLd(Person(name="Ada"))
    restored = Script.model_validate_json(tag.model_dump_json())
    assert str(restored) == str(tag)


def test_parses_back_and_still_renders_identically():
    tag = JsonLd(Person(name="Ada", email="ada@example.com"))
    parsed = from_html(str(tag), parser="html.parser")
    assert str(parsed) == str(tag)
    assert json.loads(parsed.text)["email"] == "ada@example.com"


def test_non_ascii_is_not_mangled():
    """ensure_ascii is off, so UTF-8 goes out as itself and stays shorter."""
    tag = JsonLd({"name": "Ada Lovelace — 日本語"})
    assert "日本語" in str(tag)
    assert payload(tag)["name"] == "Ada Lovelace — 日本語"
