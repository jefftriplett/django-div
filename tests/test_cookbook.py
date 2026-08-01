"""Every recipe in docs/cookbook.md and docs/django-cookbook.md.

The code here is the code the docs show. If a recipe changes in one place it
has to change in the other, and this file is what catches it.
"""

import json
from urllib.parse import urljoin

import pytest
from django import forms
from django.template import Context, Engine, Library
from django.test import RequestFactory

from django_div import (
    H1,
    H2,
    A,
    Body,
    Button,
    Div,
    Form,
    Head,
    Html,
    Input,
    Label,
    Li,
    Meta,
    Nav,
    Ol,
    P,
    Raw,
    Script,
    Span,
    Table,
    Tag,
    Tbody,
    Td,
    Text,
    Th,
    Thead,
    Title,
    Tr,
    Ul,
    from_html,
    parse,
    tag_class,
)
from django_div.django import as_response, csrf_input

# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def card(title, *body, href=None):
    heading = A(title, href=href) if href else title
    return Div(H2(heading), Div(*body, class_="card-body"), class_="card")


def test_component():
    assert str(card("Hello", P("Body"), href="/x")) == (
        '<div class="card"><h2><a href="/x">Hello</a></h2>'
        '<div class="card-body"><p>Body</p></div></div>'
    )


def document(title, *body, lang="en"):
    return [
        Raw(content="<!DOCTYPE html>"),
        Html(Head(Meta(charset="utf-8"), Title(title)), Body(*body), lang=lang),
    ]


def render(items):
    return "".join(str(item) for item in items)


def test_document():
    assert render(document("Home", H1("Hi"))) == (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8" />'
        "<title>Home</title></head><body><h1>Hi</h1></body></html>"
    )


def data_table(rows, columns):
    return Table(
        Thead(Tr(Th(column) for column in columns)),
        Tbody(Tr(Td(row[column]) for column in columns) for row in rows),
    )


def test_data_table():
    assert str(data_table([{"name": "Ana", "age": 33}], ["name", "age"])) == (
        "<table><thead><tr><th>name</th><th>age</th></tr></thead>"
        "<tbody><tr><td>Ana</td><td>33</td></tr></tbody></table>"
    )


def nav(links, current):
    return Nav(
        Ul(
            Li(A(label, href=url, class_={"active": url == current}))
            for label, url in links
        )
    )


def test_nav_marks_the_current_page():
    assert str(nav([("Home", "/"), ("Docs", "/docs/")], "/docs/")) == (
        '<nav><ul><li><a href="/">Home</a></li>'
        '<li><a href="/docs/" class="active">Docs</a></li></ul></nav>'
    )


def test_generator_needs_brackets_beside_keywords():
    """Ul(Li(x) for x in xs, class_="y") is a SyntaxError in Python."""
    source = 'Ul(Li(x) for x in ["a"], class_="errors")'
    with pytest.raises(SyntaxError):
        compile(source, "<recipe>", "eval")
    # The fix is a list comprehension.
    assert str(Ul([Li(x) for x in ["a"]], class_="errors")) == (
        '<ul class="errors"><li>a</li></ul>'
    )


def test_custom_elements():
    MyWidget = tag_class("my-widget")
    assert str(MyWidget("hi", data_state="ready")) == (
        '<my-widget data-state="ready">hi</my-widget>'
    )


def icon(name, size=16):
    Svg = tag_class("svg")
    Use = tag_class("use")
    return Svg(
        Use(href=f"/static/icons.svg#{name}"),
        width=size,
        height=size,
        aria_hidden="true",
    )


def test_svg_icon():
    assert str(icon("check")) == (
        '<svg width="16" height="16" aria-hidden="true">'
        '<use href="/static/icons.svg#check"></use></svg>'
    )


def test_xml_with_generic_tag():
    feed = Tag(
        "rss",
        Tag("channel", Tag("title", "News"), Tag("item", Tag("title", "First"))),
        version="2.0",
    )
    assert str(feed) == (
        '<rss version="2.0"><channel><title>News</title>'
        "<item><title>First</title></item></channel></rss>"
    )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_extract_links():
    page = from_html('<div><a href="/a">A</a><p><a href="/b">B</a></p></div>')
    assert [(a.text, a.attrs["href"]) for a in page.find_all("a")] == [
        ("A", "/a"),
        ("B", "/b"),
    ]


def absolutize(tree, base):
    for link in tree.find_all("a"):
        if "href" in link.attrs:
            link.attrs["href"] = urljoin(base, link.attrs["href"])
    return tree


def test_absolutize():
    tree = from_html('<div><a href="/a">A</a></div>')
    assert str(absolutize(tree, "https://example.test/")) == (
        '<div><a href="https://example.test/a">A</a></div>'
    )


def table_of_contents(tree, levels=("h2", "h3")):
    return Ul(
        Li(A(heading.text, href="#" + heading.attrs["id"]))
        for heading in tree.find_all()
        if heading.tag in levels and "id" in heading.attrs
    )


def test_table_of_contents():
    tree = from_html('<div><h2 id="a">A</h2><p>x</p><h2 id="b">B</h2></div>')
    assert str(table_of_contents(tree)) == (
        '<ul><li><a href="#a">A</a></li><li><a href="#b">B</a></li></ul>'
    )


def cells(row):
    return [cell.text.strip() for cell in row.find_all() if cell.tag in {"th", "td"}]


def table_to_dicts(table):
    rows = table.find_all("tr")
    headers = cells(rows[0])
    return [dict(zip(headers, cells(row))) for row in rows[1:]]


def test_scrape_a_table():
    table = from_html(
        "<table><tr><th>name</th><th>age</th></tr>"
        "<tr><td>Ana</td><td>33</td></tr></table>"
    )
    assert table_to_dicts(table) == [{"name": "Ana", "age": "33"}]


KEEP = {"p", "b", "i", "em", "strong", "a", "ul", "ol", "li", "code", "br"}
KEEP_ATTRS = {"a": {"href", "title"}}
DROP_ENTIRELY = {"script", "style"}


def keep_only(items):
    """Reduce a tree to an allowlist of elements. Not a security boundary."""
    kept = []
    for item in items:
        if isinstance(item, Text):
            kept.append(item)
        elif isinstance(item, Tag):
            if item.tag in DROP_ENTIRELY:
                continue
            if item.tag not in KEEP:
                kept.extend(keep_only(item.children))
                continue
            item.children = keep_only(item.children)
            item.attrs = {
                name: value
                for name, value in item.attrs.items()
                if name in KEEP_ATTRS.get(item.tag, set())
            }
            kept.append(item)
    return kept


def test_keep_only_strips_elements_and_attributes():
    dirty = parse('<p onclick="evil()">ok <script>alert(1)</script><b>b</b></p>')
    assert render(keep_only(dirty)) == "<p>ok <b>b</b></p>"


def readable_text(tree, separator=" "):
    """Text with a separator between blocks, unlike .text which concatenates."""
    return separator.join(
        part
        for part in (
            item.content.strip() for item in tree.walk() if isinstance(item, Text)
        )
        if part
    )


def test_readable_text():
    tree = from_html("<article><h1>Title</h1><p>one two</p></article>")
    assert tree.text == "Titleone two", "walk order, no separators"
    assert readable_text(tree) == "Title one two"


def pretty(item, indent=0):
    pad = "  " * indent
    if not isinstance(item, Tag):
        text = str(item).strip()
        return [pad + text] if text else []
    if item.is_void:
        return [pad + str(item)]
    opening = str(item).split(">", 1)[0] + ">"
    lines = [pad + opening]
    for child in item.children:
        lines += pretty(child, indent + 1)
    return [*lines, pad + f"</{item.tag}>"]


def test_pretty_print():
    assert pretty(from_html("<div><p>hi</p></div>")) == [
        "<div>",
        "  <p>",
        "    hi",
        "  </p>",
        "</div>",
    ]


# ---------------------------------------------------------------------------
# Serializing
# ---------------------------------------------------------------------------


def test_cache_a_parsed_page():
    tree = from_html('<div class="card"><p>hi</p></div>')
    cached = tree.model_dump_json()
    assert str(Tag.model_validate_json(cached)) == str(tree)


def test_compare_structurally():
    assert from_html("<div><p>x</p></div>") == from_html("<div><p>x</p></div>")
    assert from_html("<div><p>x</p></div>") != from_html("<div><p>y</p></div>")


def test_assert_on_structure_not_strings():
    page = from_html('<form><input name="q" /><button>Go</button></form>')
    assert page.find("input").attrs["name"] == "q"
    assert page.find("button").text == "Go"


# ---------------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------------

register = Library()


@register.simple_tag
def badge(text, tone="info"):
    return Span(text, class_=["badge", f"badge-{tone}"]).render()


def test_simple_tag_returns_markup():
    assert (
        badge("New", tone="success") == '<span class="badge badge-success">New</span>'
    )


def test_simple_tag_in_a_template():
    engine = Engine(libraries={"ui": "tests.test_cookbook"})
    template = engine.from_string("{% load ui %}{% badge 'New' tone='success' %}")
    assert template.render(Context({})) == (
        '<span class="badge badge-success">New</span>'
    )


def test_tag_in_template_context_is_not_escaped():
    engine = Engine(libraries={})
    template = engine.from_string("{{ card }}")
    assert template.render(Context({"card": Div(H2("Hi"), class_="card")})) == (
        '<div class="card"><h2>Hi</h2></div>'
    )


class ContactForm(forms.Form):
    email = forms.EmailField(label="Email")


def render_field(field):
    return Div(
        Label(field.label, for_=field.id_for_label),
        Raw(content=str(field)),
        field.errors and Ul([Li(error) for error in field.errors], class_="errors"),
        class_="field",
    )


def test_render_a_form_field_with_errors():
    form = ContactForm(data={"email": "nope"})
    rendered = str(render_field(form["email"]))
    assert rendered.startswith('<div class="field"><label for="id_email">Email</label>')
    assert '<ul class="errors"><li>Enter a valid email address.</li></ul>' in rendered
    assert "&lt;input" not in rendered, "the widget's own markup must survive"


def with_class(widget_html, css_class):
    tree = from_html(str(widget_html))
    existing = tree.attrs.get("class")
    tree.attrs["class"] = " ".join(filter(None, [existing, css_class]))
    return tree


def test_add_a_class_to_a_widget():
    form = ContactForm()
    assert 'class="form-control"' in str(with_class(form["email"], "form-control"))


def json_script(data, id):
    """json.dumps can emit </script>; escaping < keeps it inside the element."""
    return Script(
        json.dumps(data).replace("<", "\\u003C"), id=id, type="application/json"
    )


def test_json_script_cannot_break_out():
    rendered = str(json_script({"a": "</script>"}, "config"))
    assert rendered == (
        '<script id="config" type="application/json">{"a": "\\u003C/script>"}</script>'
    )
    assert "</script><" not in rendered


def alerts(messages):
    return Div(
        [
            Div(message, class_=["alert", f"alert-{level}"])
            for level, message in messages
        ],
        class_="messages",
    )


def test_alerts():
    assert str(alerts([("info", "Saved")])) == (
        '<div class="messages"><div class="alert alert-info">Saved</div></div>'
    )


def pagination(number, num_pages, base="?page="):
    return Nav(
        Ul(
            Li(A("Previous", href=f"{base}{number - 1}")) if number > 1 else None,
            [
                Li(A(str(n), href=f"{base}{n}", class_={"current": n == number}))
                for n in range(1, num_pages + 1)
            ],
            Li(A("Next", href=f"{base}{number + 1}")) if number < num_pages else None,
        ),
        class_="pagination",
    )


def test_pagination():
    rendered = str(pagination(1, 2))
    assert "Previous" not in rendered, "no previous link on the first page"
    assert '<a href="?page=1" class="current">1</a>' in rendered
    assert "Next" in rendered


def breadcrumbs(trail):
    items = []
    for index, (label, url) in enumerate(trail):
        last = index == len(trail) - 1
        items.append(Li(label if last else A(label, href=url), class_={"active": last}))
    return Nav(Ol(items, class_="breadcrumb"), aria_label="Breadcrumb")


def test_breadcrumbs():
    assert str(breadcrumbs([("Home", "/"), ("Building", None)])) == (
        '<nav aria-label="Breadcrumb"><ol class="breadcrumb">'
        '<li><a href="/">Home</a></li>'
        '<li class="active">Building</li></ol></nav>'
    )


def item_row(item):
    return Tr(
        Td(item["name"]),
        Td(
            Button(
                "Delete",
                hx_delete=f"/items/{item['id']}/",
                hx_target="closest tr",
                hx_swap="outerHTML",
            )
        ),
        id=f"item-{item['id']}",
    )


def test_htmx_row():
    assert str(item_row({"id": 3, "name": "Ana"})) == (
        '<tr id="item-3"><td>Ana</td><td>'
        '<button hx-delete="/items/3/" hx-target="closest tr" '
        'hx-swap="outerHTML">Delete</button></td></tr>'
    )


def test_as_response():
    response = as_response(Div("hi"))
    assert response.status_code == 200
    assert response.content == b"<div>hi</div>"


def test_csrf_form():
    request = RequestFactory().get("/")
    rendered = str(
        Form(csrf_input(request), Input(name="q"), Button("Go"), method="post")
    )
    assert 'name="csrfmiddlewaretoken"' in rendered
    assert "&lt;input" not in rendered


def test_html_email():
    body = render(document("Receipt", P("Hi Ana"), lang="en"))
    assert body.startswith("<!DOCTYPE html>")
    assert "<p>Hi Ana</p>" in body
