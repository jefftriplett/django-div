import typer

from pydantic import BaseModel, Field
from typing import List, Union, Optional
from html import escape


class HtmlItem(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class Text(HtmlItem):
    content: str

    def __str__(self):
        return escape(self.content)


# Base class for all tag types, similar to before but designed to be inherited
class Tag(HtmlItem):
    tag: Optional[str] = None  # We'll override this in subclasses
    children: List[Union["Tag", Text]] = Field(default_factory=list)
    attrs: dict = Field(default_factory=dict)

    def __init__(
        __pydantic_self__,
        *children: Union["Tag", Text, None, str],
        **attrs: Union[str, bool],
    ):
        # The tag is now set by the class attribute
        super().__init__(
            tag=__pydantic_self__.tag, attrs=attrs, children=list(children)
        )

    def __str__(self):
        attrs_str = " ".join(
            f'{key}="{value}"'
            for key, value in self.attrs.items()
            if value is not False
        )
        attrs_str = f" {attrs_str}" if attrs_str else ""
        children_str = "".join(str(child) for child in self.children)
        tag = self.tag if self.tag else ""
        return f"<{tag}{attrs_str}>{children_str}</{tag}>"


# Specific tag classes
class Div(Tag):
    tag = "div"


class A(Tag):
    tag = "a"


class Br(Tag):
    tag = "br"
    children: List = Field(default_factory=list)

    def __str__(self):
        attrs_str = " ".join(
            f'{key}="{value}"'
            for key, value in self.attrs.items()
            if value is not False
        )
        return f"<{self.tag} {attrs_str}/>"  # Self-closing tag representation


class Img(Tag):
    tag = "img"

    def __str__(self):
        # Assuming all necessary attributes are handled, including alt for accessibility
        attrs_str = " ".join(f'{key}="{value}"' for key, value in self.attrs.items())
        return f"<{self.tag} {attrs_str}/>"  # Self-closing tag representation


# Usage example
def main():
    page_content = Div(
        A(href="https://example.com", children=[Text(content="Click Here")]),
        Br(),
        Img(src="image.png", alt="A sample image"),
    )

    print(page_content)


if __name__ == "__main__":
    typer.run(main)
