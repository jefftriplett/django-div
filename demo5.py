import typer

from html import escape
from pydantic import BaseModel
from pydantic import Field
from typing import List
from typing import Union


class HtmlItem(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"


class Tag(HtmlItem):
    children: List[Union["Tag", "Text"]] = Field(default_factory=list)
    attrs: dict = Field(default_factory=dict)

    @property
    def tag(self) -> str:
        raise NotImplementedError("Tag name not defined in base Tag class")

    def __str__(self) -> str:
        attrs_str = " ".join(
            f'{key}="{value}"'
            for key, value in self.attrs.items()
            if value is not False
        )
        attrs_str = f" {attrs_str}" if attrs_str else ""
        children_str = "".join(str(child) for child in self.children)
        return f"<{self.tag}{attrs_str}>{children_str}</{self.tag}>"


class Text(HtmlItem):
    content: str

    def __str__(self) -> str:
        return escape(self.content)


class A(Tag):

    @property
    def tag(self) -> str:
        return "a"


class Br(Tag):
    def __str__(self) -> str:
        attrs_str = " ".join(
            f'{key}="{value}"'
            for key, value in self.attrs.items()
            if value is not False
        )
        return f"<br {attrs_str}/>"  # Note: Self-closing tags like <br> don't have children


class Div(Tag):
    @property
    def tag(self) -> str:
        return "div"


class Img(Tag):
    @property
    def tag(self) -> str:
        return "img"

    def __str__(self) -> str:
        # Img tags specifically handle `src` and `alt` attributes for this example
        attrs_str = " ".join(f'{key}="{value}"' for key, value in self.attrs.items())
        return f"<img {attrs_str}/>"


# class HtmlItem(BaseModel):
#     class Config:
#         arbitrary_types_allowed = True


# class Text(HtmlItem):
#     content: str

#     def __str__(self) -> str:
#         return escape(self.content)


# # Base class for HTML tags
# class Tag(HtmlItem):
#     tag: str  # This will be set to a literal type in subclasses
#     children: List[Union["Tag", Text]] = Field(default_factory=list)
#     attrs: dict = Field(default_factory=dict)

#     def __str__(self) -> str:
#         attrs_str = " ".join(
#             f'{key}="{value}"'
#             for key, value in self.attrs.items()
#             if value is not False
#         )
#         attrs_str = f" {attrs_str}" if attrs_str else ""
#         children_str = "".join(str(child) for child in self.children)
#         return f"<{self.tag}{attrs_str}>{children_str}</{self.tag}>"


# Factory function to create tag-specific classes with a constant `tag` value
# def create_tag_class(tag_name: str) -> type:
#     # Note: Using Literal for a single value essentially sets it as a constant
#     tag_field = Field(default=Literal[tag_name])
#     return type(tag_name.capitalize(), (Tag,), {"tag": tag_field})


# # Creating specific tag classes using the factory function
# Div = create_tag_class("div")
# A = create_tag_class("a")
# Br = create_tag_class("br")
# Img = create_tag_class("img")


# Example usage
def main():
    page_content = Div(
        children=[
            A(href="https://example.com", children=[Text(content="Click Here")]),
            Br(),
            Img(src="image.png", alt="A sample image"),
        ]
    )

    print(page_content)


if __name__ == "__main__":
    typer.run(main)
