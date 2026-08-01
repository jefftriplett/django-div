"""to_markdown() and from_markdown()."""

from django_div import (
    H1,
    H2,
    A,
    B,
    Blockquote,
    Br,
    Code,
    Comment,
    Div,
    Em,
    Hr,
    Img,
    Li,
    Ol,
    P,
    Pre,
    Script,
    Span,
    Strong,
    Table,
    Tag,
    Tbody,
    Td,
    Th,
    Thead,
    Tr,
    Ul,
    from_html,
)
from django_div.markdown import from_markdown, to_markdown

# --- blocks -----------------------------------------------------------------


def test_headings():
    assert to_markdown(H1("Title")) == "# Title"
    assert to_markdown(H2("Sub")) == "## Sub"


def test_paragraphs_are_separated_by_blank_lines():
    assert to_markdown(Div(P("one"), P("two"))) == "one\n\ntwo"


def test_containers_disappear():
    assert to_markdown(Div(Div(P("deep")))) == "deep"


def test_hr():
    assert to_markdown(Hr()) == "---"


def test_blockquote():
    assert to_markdown(Blockquote(P("a"), P("b"))) == "> a\n>\n> b"


def test_code_fence_with_language():
    pre = Pre(Code("if a < b:\n    go()", class_="language-python"))
    assert to_markdown(pre) == "```python\nif a < b:\n    go()\n```"


def test_code_fence_grows_past_backticks_in_content():
    assert to_markdown(Pre("a ``` b")) == "````\na ``` b\n````"


def test_unordered_list():
    assert to_markdown(Ul(Li("one"), Li("two"))) == "- one\n- two"


def test_ordered_list_honors_start():
    assert to_markdown(Ol(Li("three"), Li("four"), start=3)) == "3. three\n4. four"


def test_nested_list_indents():
    tree = Ul(Li("top", Ul(Li("inner"))))
    assert to_markdown(tree) == "- top\n    - inner"


def test_table():
    table = Table(
        Thead(Tr(Th("Name"), Th("Age"))),
        Tbody(Tr(Td("Ana"), Td("33"))),
    )
    assert to_markdown(table) == ("| Name | Age |\n| --- | --- |\n| Ana | 33 |")


def test_table_cells_escape_pipes():
    table = Table(Tr(Th("a|b")))
    assert r"a\|b" in to_markdown(table)


def test_script_and_style_are_dropped():
    assert to_markdown(Div(Script("evil()"), P("kept"))) == "kept"


def test_comments_survive():
    assert to_markdown(Div(Comment(content="note"), P("x"))) == "<!--note-->\n\nx"


# --- inline -----------------------------------------------------------------


def test_inline_wrappers():
    assert to_markdown(P(Em("it"), " and ", Strong("bold"))) == "*it* and **bold**"
    assert to_markdown(P(B("b"))) == "**b**"


def test_links_and_images():
    assert to_markdown(P(A("docs", href="/docs"))) == "[docs](/docs)"
    assert to_markdown(P(A("t", href="/x", title="Tip"))) == '[t](/x "Tip")'
    assert to_markdown(P(Img(src="a.png", alt="A cat"))) == "![A cat](a.png)"


def test_inline_code_grows_past_backticks():
    assert to_markdown(P(Code("uses ` tick"))) == "`` uses ` tick ``"


def test_hard_break():
    assert to_markdown(P("one", Br(), "two")) == "one\\\ntwo"


def test_transparent_inline_tags_flow_through():
    assert to_markdown(P(Span("plain"))) == "plain"


def test_unrepresentable_tags_fall_back_to_html():
    # <video> has no Markdown form; Markdown permits inline HTML.
    assert to_markdown(P(Tag("video", src="a.mp4"))) == '<video src="a.mp4"></video>'


def test_attributes_are_dropped():
    # Lossy on purpose: class and id have no Markdown representation.
    assert to_markdown(P("x", class_="lead", id="intro")) == "x"


def test_list_input_renders_each_root():
    assert to_markdown([H1("A"), P("b")]) == "# A\n\nb"


# --- the pipeline: HTML in, Markdown out ------------------------------------


def test_from_html_to_markdown():
    html = "<article><h1>Title</h1><p>Body with <a href='/x'>a link</a>.</p></article>"
    assert to_markdown(from_html(html)) == "# Title\n\nBody with [a link](/x)."


# --- from_markdown ----------------------------------------------------------


def test_from_markdown_returns_a_tree():
    tree = from_markdown("# Title\n\nBody text.")
    assert isinstance(tree, list)
    assert tree[0].tag == "h1"
    assert tree[0].text == "Title"


def test_from_markdown_single_root_unwraps():
    item = from_markdown("just a paragraph")
    assert item.tag == "p"


def test_from_markdown_gfm_table_and_strikethrough():
    items = from_markdown("| a |\n| --- |\n| b |\n\n~~gone~~")
    table = items[0]
    assert table.tag == "table"
    assert table.find("td").text == "b"
    assert items[1].find("s") is not None


def test_markdown_round_trip_is_stable():
    source = "# Title\n\n- one\n- two\n\n> quoted"
    once = to_markdown(from_markdown(source))
    assert to_markdown(from_markdown(once)) == once


def test_to_markdown_of_docstring_example():
    assert to_markdown(Div(H1("Title"), P("Body text."))) == "# Title\n\nBody text."
