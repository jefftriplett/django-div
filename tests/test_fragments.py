import pytest
from pydantic import ValidationError

from django_div import H1, Comment, Div, Doctype, Fragment, P, Raw, Tag, Text, parse
from django_div.markdown import to_markdown


def test_fragment_coerces_children_and_renders_without_wrapper():
    fragment = Fragment(
        Doctype(), H1("Title"), [None, False, "<&"], (P(i) for i in range(2))
    )
    assert str(fragment) == "<!DOCTYPE html><h1>Title</h1>&lt;&amp;<p>0</p><p>1</p>"
    assert str(Fragment()) == ""
    assert str(Div(Fragment(P("a"), P("b")))) == "<div><p>a</p><p>b</p></div>"


def test_fragment_traversal_search_and_text():
    paragraph = P(" Body ", id="body")
    nested = Fragment(paragraph)
    fragment = Fragment(
        H1("Title"), nested, Comment(content="note"), Raw(content="<b>x</b>")
    )
    assert fragment.find("p", id="body") is paragraph
    assert fragment.find_all() == [fragment.children[0], paragraph]
    assert list(fragment.iter_find("p")) == [paragraph]
    assert list(fragment.walk())[3] is nested
    assert fragment.text == "Title Body "
    assert fragment.get_text(" ", strip=True) == "Title Body"
    assert Div(fragment).find("p") is paragraph


@pytest.mark.parametrize("json", [False, True])
def test_fragment_round_trip_restores_nested_classes(json):
    original = Fragment(Doctype(), H1("Title"), Fragment(P("Body")))
    restored = (
        Fragment.model_validate_json(original.model_dump_json())
        if json
        else Fragment.model_validate(original.model_dump())
    )
    assert restored == original
    assert isinstance(restored.children[1], H1)
    assert isinstance(restored.children[2], Fragment)
    assert isinstance(restored.children[2].children[0], P)
    tree = Div(original)
    restored_tree = Tag.model_validate_json(tree.model_dump_json())
    assert isinstance(restored_tree.children[0], Fragment)
    assert str(restored_tree) == str(tree)


def test_fragment_validates_serialized_children_and_discriminator():
    with pytest.raises(ValidationError):
        Fragment.model_validate({"type": "tag", "children": []})
    with pytest.raises(ValidationError):
        Fragment.model_validate({"type": "fragment", "children": [123]})
    with pytest.raises(TypeError, match="not both"):
        Fragment(P("a"), children=[])


def test_fragment_copy_has_independent_children():
    original = Fragment(P("a"))
    clone = original(P("b"))
    clone.children.append(Text(content="c"))
    assert str(original) == "<p>a</p>"
    assert str(clone) == "<p>a</p><p>b</p>c"


def test_deep_mixed_fragments_render_and_walk_iteratively():
    root = tip = Fragment()
    for i in range(3000):
        child = Div() if i % 2 else Fragment()
        tip.children.append(child)
        tip = child
    tip.children.append(P("end"))
    assert str(root) == "<div>" * 1500 + "<p>end</p>" + "</div>" * 1500
    assert len(list(root.walk())) == 3003
    assert root.find("p").text == "end"


def test_fragment_honors_custom_renderers():
    class Special(Fragment):
        def __str__(self):
            return "<b>custom</b>"

    assert str(Div(Special())) == "<div><b>custom</b></div>"


def test_fragment_wraps_parsed_roots():
    assert str(Fragment(parse("<p>a</p><p>b</p>"))) == "<p>a</p><p>b</p>"


def test_fragment_markdown_uses_surrounding_context():
    assert to_markdown(Fragment(H1("Title"), Fragment(P("Body")))) == "# Title\n\nBody"
    assert to_markdown(P("a", Fragment("b", "c"), "d")) == "abcd"


def test_fragment_raw_text_keeps_code_and_rejects_split_closing_tags():
    from django_div import Script, Style

    assert str(Script(Fragment("if (a < b)", Fragment(" { go() }")))) == (
        "<script>if (a < b) { go() }</script>"
    )
    assert str(Style(Fragment("a > b { color: red }"))) == (
        "<style>a > b { color: red }</style>"
    )
    with pytest.raises(ValueError, match="would end the element"):
        str(Script(Fragment("</scr", Fragment("ipt>"))))


def test_fragments_in_markdown_structures_match_unwrapped_trees():
    from django_div import (
        Code,
        Dd,
        Dl,
        Dt,
        Li,
        Pre,
        Table,
        Tbody,
        Td,
        Th,
        Thead,
        Tr,
        Ul,
    )

    nested = Ul(Fragment(Li("child")))
    lists = Ul(Fragment(Li(Fragment("parent", nested))))
    assert to_markdown(lists) == "- parent\n    - child"
    definitions = Dl(Fragment(Dt("term"), Dd("definition")))
    assert to_markdown(definitions) == "term\n:   definition"
    pre = Pre(Fragment(Code("x", class_=["language-python"])))
    assert to_markdown(pre) == "```python\nx\n```"
    table = Table(
        Fragment(
            Thead(Fragment(Tr(Fragment(Th("Title"))))),
            Tbody(Fragment(Tr(Fragment(Td(Fragment(P("a"), P("b"))))))),
        )
    )
    assert to_markdown(table) == "| Title |\n| --- |\n| a<br>b |"


@pytest.mark.parametrize("base", [Div, Fragment])
def test_custom_renderer_can_delegate_to_super(base):
    class Wrapped(base):
        def __str__(self):
            return "<main>" + super().__str__() + "</main>"

    child = Wrapped("<&")
    inner = "<div>&lt;&amp;</div>" if base is Div else "&lt;&amp;"
    expected = f"<main>{inner}</main>"
    assert str(child) == expected
    assert str(Div(child)) == f"<div>{expected}</div>"
    assert str(Fragment(child)) == expected
