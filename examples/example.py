"""What django_div can do, in one runnable file.

just bootstrap
python example.py
"""

import typer
from rich import print

from django_div import (
    H1,
    A,
    Br,
    Div,
    Img,
    Input,
    Li,
    P,
    Script,
    Span,
    Style,
    Tag,
    Ul,
    best_parser,
    from_html,
)


def show(title: str, value: object) -> None:
    print(f"\n[bold cyan]{title}[/bold cyan]")
    print(f"  {value}")


def building() -> None:
    """Children are positional, attributes are keyword arguments."""
    show(
        "nesting",
        Div(
            H1("Welcome"),
            P("This is a paragraph with ", A("a link", href="#"), "."),
            Img(src="image.jpg", alt="A beautiful image"),
            Br(),
            class_="page",
        ),
    )

    # The generic Tag still works for anything not pre-generated.
    show("custom element", Tag("my-widget", "hi", data_state="ready"))


def attributes() -> None:
    """Python spellings map onto HTML ones, and falsy attributes drop out."""
    show("class_ and data_*", Div(class_="card", data_test_id="hero"))
    show("boolean attrs", Input(type="checkbox", checked=True, disabled=False))
    show("class as a list", Div(class_=["btn", "btn-primary"]))
    show("class as a mapping", Div(class_={"btn": True, "is-active": False}))
    show("style as a mapping", Div(style={"color": "red", "font_size": "2rem"}))


def escaping() -> None:
    """Text children are escaped, so user input is safe by default."""
    show("escaped text", Div("<script>alert(1)</script>"))
    show("escaped attribute", Div(title='he said "hi"'))

    # ...but script and style hold code, not text, so they are left alone.
    show("script is raw text", Script("if (a < b && c) { go() }"))
    show("style is raw text", Style("a > b { color: red }"))


def control_flow() -> None:
    """None and False drop out; iterables flatten."""
    user = None
    show("inline conditional", Div("Hello", user and Span(user)))
    show("comprehension", Ul(Li(item) for item in ["one", "two", "three"]))

    # Build in stages by calling a tag to append children.
    card = Div(class_="card")
    show("staged build", card(H1("Title"), P("Body")))


def parsing() -> None:
    """from_html() gives back the same kind of tree the constructors build."""
    html = """
    <div class="content">
        <h1>Welcome to My Page</h1>
        <p>A paragraph with <a href="/docs" target="_blank">a link</a>.</p>
        <img src="image.jpg" alt="A beautiful image">
    </div>
    """
    page = from_html(html)

    show("parser in use", best_parser())
    show("parsed type", type(page).__name__)
    show("all text", page.text)
    show("find", page.find("a").attrs)
    show("find_all", [tag.tag for tag in page.find_all()])

    # Parsed trees are editable, then re-renderable.
    for link in page.find_all("a", target="_blank"):
        link.attrs["rel"] = "noopener"
    show("edited and re-rendered", page)


def serializing() -> None:
    """Because these are Pydantic models, a tree round-trips through JSON."""
    tree = from_html('<div class="card"><p>hi <b>there</b></p></div>')
    payload = tree.model_dump_json()
    show("as JSON", payload)
    show("back from JSON", Tag.model_validate_json(payload))


def main() -> None:
    building()
    attributes()
    escaping()
    control_flow()
    parsing()
    serializing()


if __name__ == "__main__":
    typer.run(main)
