import typer

from html import escape
from pydantic import BaseModel, Field
from typing import List, Union


# Define the base class for all HTML items
class HtmlItem(BaseModel):
    class Config:
        arbitrary_types_allowed = True


# Define a class for text content within HTML
class Text(HtmlItem):
    content: str

    def __str__(self):
        return escape(self.content)


# Define a class for representing HTML tags
class Tag(HtmlItem):
    tag: str
    children: List[Union["Tag", Text]] = Field(default_factory=list)
    attrs: dict = Field(default_factory=dict)
    is_void: bool = Field(default=False)

    def __init__(
        __pydantic_self__,
        _tag: str,
        *children: Union["Tag", Text, None, str],
        **attrs: Union[str, bool],
    ):
        super().__init__(tag=_tag, attrs=attrs)
        __pydantic_self__.is_void = _tag in void_tags
        __pydantic_self__._set_children(children)

    def _set_children(self, children):
        for child in children:
            if isinstance(child, HtmlItem):
                self.children.append(child)
            elif child is None:
                continue  # Allows for conditional children
            else:
                self.children.append(Text(content=str(child)))

    def __str__(self):
        attrs_str = " ".join(
            f'{key}="{value}"'
            for key, value in self.attrs.items()
            if value is not False
        )
        attrs_str = f" {attrs_str}" if attrs_str else ""
        children_str = "".join(str(child) for child in self.children)
        if self.is_void:
            return f"<{self.tag}{attrs_str} />"
        else:
            return f"<{self.tag}{attrs_str}>{children_str}</{self.tag}>"


# A list of all void (self-closing) HTML elements
void_tags = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


# Example usage of the classes
def main():
    # Example: A div with a paragraph and a self-closing br tag inside
    div = Tag(
        "div", Tag("p", Text(content="Hello, World!")), Tag("br"), style="color: red;"
    )

    print(div)


if __name__ == "__main__":
    typer.run(main)
