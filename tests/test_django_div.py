import pytest

from django_div import (
    A,
    Br,
    Comment,
    Del,
    Div,
    Img,
    Input,
    Li,
    P,
    Raw,
    Script,
    Span,
    Style,
    Tag,
    Text,
    Ul,
    best_parser,
    from_html,
    normalize_attr,
    parse,
)


def test_nesting_and_attrs():
    assert (
        str(Div(P("Hello, World!"), A("Click", href="/x"), class_="card"))
        == '<div class="card"><p>Hello, World!</p><a href="/x">Click</a></div>'
    )


def test_void_tags_self_close():
    assert str(Br()) == "<br />"
    assert str(Img(src="a.png", alt="A cat")) == '<img src="a.png" alt="A cat" />'


def test_generic_tag_still_works():
    assert str(Tag("div", Tag("p", "hi"))) == "<div><p>hi</p></div>"


def test_text_is_escaped():
    assert str(Div("<script>alert(1)</script>")) == (
        "<div>&lt;script&gt;alert(1)&lt;/script&gt;</div>"
    )


def test_attr_values_are_escaped():
    assert (
        str(Div(title='he said "hi"')) == '<div title="he said &quot;hi&quot;"></div>'
    )


def test_raw_passes_through():
    assert str(Div(Raw(content="<b>bold</b>"))) == "<div><b>bold</b></div>"


def test_comment():
    assert str(Comment(content="note")) == "<!--note-->"


@pytest.mark.parametrize(
    "python_name,html_name",
    [
        ("class_", "class"),
        ("for_", "for"),
        ("data_test_id", "data-test-id"),
        ("aria_label", "aria-label"),
        ("hx_get", "hx-get"),
        ("http_equiv", "http-equiv"),
        ("style", "style"),
    ],
)
def test_normalize_attr(python_name, html_name):
    assert normalize_attr(python_name) == html_name


def test_boolean_attrs():
    assert str(Input(disabled=True, type="text")) == '<input disabled type="text" />'
    assert str(Input(disabled=False)) == "<input />"
    assert str(Input(disabled=None)) == "<input />"


def test_class_accepts_list_and_dict():
    assert str(Div(class_=["a", "b"])) == '<div class="a b"></div>'
    assert str(Div(class_={"on": True, "off": False})) == '<div class="on"></div>'


def test_none_and_false_children_are_dropped():
    user = None
    assert str(Div("hi", user and P("name"), False)) == "<div>hi</div>"


def test_iterable_children_are_flattened():
    assert str(Ul(Li(n) for n in range(3))) == "<ul><li>0</li><li>1</li><li>2</li></ul>"
    assert str(Div([Span("a"), Span("b")])) == "<div><span>a</span><span>b</span></div>"


def test_call_appends_children():
    card = Div(class_="card")
    assert str(card(P("body"))) == '<div class="card"><p>body</p></div>'
    assert str(card) == '<div class="card"></div>', "original must be unchanged"


def test_html_protocol():
    assert Div("hi").__html__() == "<div>hi</div>"
    assert Div("hi").render() == "<div>hi</div>"


def test_subclasses_keep_their_type_as_children():
    div = Div(P("x"))
    assert isinstance(div.children[0], P)


def test_attrs_are_normalized_at_construction():
    assert Div(class_="card", data_id="1").attrs == {"class": "card", "data-id": "1"}


def test_model_dump_keeps_nested_subclass_fields():
    # Without SerializeAsAny, pydantic v2 dumps children as empty dicts.
    assert Div(P("x"), class_="card").model_dump() == {
        "type": "tag",
        "tag": "div",
        "attrs": {"class": "card"},
        "children": [
            {
                "type": "tag",
                "tag": "p",
                "attrs": {},
                "children": [{"type": "text", "content": "x"}],
            },
        ],
    }


def test_model_validate_restores_the_tree():
    tree = Div(P("hi"), Img(src="x.png"), Comment(content="c"), class_="card")
    restored = Tag.model_validate(tree.model_dump())
    assert str(restored) == str(tree)
    assert isinstance(restored.children[0], P)
    assert isinstance(restored.children[2], Comment)


def test_model_dump_json_round_trips():
    tree = from_html("<div class='a'><p>hi <b>there</b></p><br /></div>")
    assert str(Tag.model_validate_json(tree.model_dump_json())) == str(tree)


def test_from_html_roundtrip():
    html = '<div id="a" class="my-class"><p>Hello</p><img src="x.png" /></div>'
    assert str(from_html(html)) == html


def test_from_html_text_and_nesting():
    parsed = from_html("<div>hi <b>there</b></div>")
    assert isinstance(parsed, Tag)
    assert parsed.tag == "div"
    assert str(parsed) == "<div>hi <b>there</b></div>"


def test_from_html_multiple_roots():
    roots = from_html("<p>a</p><p>b</p>")
    assert isinstance(roots, list)
    assert [str(r) for r in roots] == ["<p>a</p>", "<p>b</p>"]


def test_from_html_returns_typed_tags():
    page = from_html("<div><p>hi</p></div>")
    assert isinstance(page, Div)
    assert isinstance(page.children[0], P)


def test_from_html_keeps_word_breaks_between_inline_tags():
    assert str(from_html("<p><b>a</b> <b>b</b></p>")) == "<p><b>a</b> <b>b</b></p>"


def test_from_html_drops_layout_indentation():
    html = """
    <div>
        <p>hi</p>
    </div>
    """
    assert str(from_html(html)) == "<div><p>hi</p></div>"


def test_from_html_collapses_indentation_between_siblings():
    html = """
    <div>
        <p>one</p>
        <p>two</p>
    </div>
    """
    assert str(from_html(html)) == "<div><p>one</p> <p>two</p></div>"


def test_from_html_keeps_doctype_and_comments():
    html = "<!DOCTYPE html><!--note--><p>hi</p>"
    assert "".join(str(item) for item in parse(html)) == html


def test_find_and_find_all():
    page = from_html(
        '<div><a href="/a" class="x">A</a><span><a href="/b">B</a></span></div>'
    )
    assert [a.attrs["href"] for a in page.find_all("a")] == ["/a", "/b"]
    assert page.find("a", class_="x").text == "A"
    assert page.find("nope") is None


def test_text_property():
    assert from_html("<div>hi <b>there</b>!</div>").text == "hi there!"


def test_walk_yields_every_node():
    page = from_html("<div><p>hi</p></div>")
    assert [type(item).__name__ for item in page.walk()] == ["Div", "P", "Text"]


def test_edit_parsed_tree_and_rerender():
    page = from_html('<div><a href="/x" target="_blank">Click</a></div>')
    for link in page.find_all("a", target="_blank"):
        link.attrs["rel"] = "noopener"
    assert str(page) == (
        '<div><a href="/x" target="_blank" rel="noopener">Click</a></div>'
    )


def test_text_model_direct():
    assert str(Text(content="a & b")) == "a &amp; b"


def test_script_content_is_not_escaped():
    # Escaping would change what the JavaScript means.
    assert str(Script("if (a < b && c) { x() }")) == (
        "<script>if (a < b && c) { x() }</script>"
    )


def test_style_content_is_not_escaped():
    assert str(Style("a > b { color: red }")) == "<style>a > b { color: red }</style>"


def test_script_roundtrips_through_parsing():
    html = "<script>if (a < b) { x() }</script>"
    assert str(from_html(html)) == html


def test_raw_text_refuses_to_be_broken_out_of():
    tag = Script("</script><script>alert(1)</script>")
    with pytest.raises(ValueError, match="would end the element"):
        str(tag)


def test_ordinary_tags_still_escape():
    assert str(P("a < b")) == "<p>a &lt; b</p>"


def test_pre_preserves_whitespace():
    html = "<pre>line1\n  line2\n</pre>"
    assert str(from_html(html)) == html


def test_pre_preserves_whitespace_between_children():
    html = "<pre><b>a</b>\n\n<b>b</b></pre>"
    assert str(from_html(html)) == html


def test_textarea_preserves_whitespace():
    html = "<textarea>  keep  </textarea>"
    assert str(from_html(html)) == html


def test_void_tags_reject_children():
    with pytest.raises(ValueError, match="void element"):
        Br("nope")
    with pytest.raises(ValueError, match="void element"):
        Img("nope", src="a.png")


def test_style_accepts_a_mapping():
    assert str(Div(style={"color": "red", "font_size": "2rem"})) == (
        '<div style="color: red; font-size: 2rem"></div>'
    )


def test_style_string_still_works():
    assert str(Div(style="color: red")) == '<div style="color: red"></div>'


def test_del_element_exists():
    assert str(Del("gone")) == "<del>gone</del>"


def test_best_parser_prefers_lxml_when_installed():
    assert best_parser() == "lxml"


def test_default_parser_closes_implicit_paragraphs():
    # The stdlib parser nests these instead, which is wrong.
    assert [str(item) for item in parse("<p>one<p>two")] == ["<p>one</p>", "<p>two</p>"]


def test_explicit_parser_is_honored():
    assert str(from_html("<p>hi</p>", parser="html.parser")) == "<p>hi</p>"


def test_public_functions_take_at_most_one_positional_argument():
    """Everything after the first argument is keyword-only.

    Named arguments read better at the call site and can be reordered or
    added without breaking anyone. Tag constructors follow the same rule by
    a different route: their positionals are variadic children, so anything
    named is an attribute. See test_tags.py for that half.
    """
    import inspect

    import django_div

    positional = (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
    offenders = {}
    for name in django_div.__all__:
        value = getattr(django_div, name)
        if not inspect.isfunction(value):
            continue
        parameters = inspect.signature(value).parameters.values()
        count = sum(1 for p in parameters if p.kind in positional)
        if count > 1:
            offenders[name] = count
    assert not offenders


def test_empty_class_mapping_drops_the_attribute():
    # class="" is noise; an all-false mapping means no classes at all.
    assert str(Div(class_={"active": False})) == "<div></div>"
    assert str(Div(class_=[])) == "<div></div>"
    assert str(Div(class_="")) == "<div></div>"


def test_empty_style_mapping_drops_the_attribute():
    assert str(Div(style={})) == "<div></div>"


def test_partly_true_class_mapping_still_renders():
    assert str(Div(class_={"btn": True, "active": False})) == '<div class="btn"></div>'


# --- regression tests: deep trees, clones, attribute-name safety ------------


def build_deep(depth):
    root = tip = Div()
    for _ in range(depth):
        new = Div()
        tip.children.append(new)
        tip = new
    return root


def test_deep_trees_render_walk_and_search():
    # Recursive implementations overflowed the Python stack around ~1000.
    deep = build_deep(3000)
    assert str(deep).count("<div>") == 3001
    assert sum(1 for _ in deep.walk()) == 3001
    assert deep.text == ""
    assert deep.find("p") is None


def test_deep_documents_parse():
    depth = 2500
    page = from_html("<i>" * depth + "x" + "</i>" * depth, parser="html.parser")
    assert sum(1 for _ in page.walk()) == depth + 1


def test_call_clone_does_not_share_attrs():
    card = Div(class_="card")
    clone = card(P("x"))
    clone.attrs["id"] = "mutated"
    assert card.attrs == {"class": "card"}, "the original must be untouched"


def test_attrs_named_tag_and_attrs_together_are_attributes():
    # Both at once used to be mistaken for a Pydantic validation payload.
    assert str(Tag("div", tag="v", attrs="w")) == '<div tag="v" attrs="w"></div>'


def test_malformed_attribute_names_are_refused():
    # Values are escaped; names cannot be, so a crafted name could smuggle
    # a second attribute (e.g. an onload handler) into the output.
    evil = Div(**{'x="y" onload="alert(1)': "z"})
    with pytest.raises(ValueError, match="invalid attribute name"):
        str(evil)


def test_ordinary_attribute_names_pass_validation():
    assert str(Div(data_x="1", aria_label="ok", hx_get="/x")) == (
        '<div data-x="1" aria-label="ok" hx-get="/x"></div>'
    )


def test_iter_find_is_lazy():
    tree = Div(P("hit"), P("later"))
    found = tree.iter_find("p")
    assert next(found).text == "hit"
