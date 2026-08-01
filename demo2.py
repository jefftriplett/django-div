import typer

from bs4 import BeautifulSoup
from html import escape
from pydantic import BaseModel
from pydantic import Field, validator
from pydantic import create_model
from pydantic import root_validator
from rich import print
from typing import List
from typing import Optional
from typing import Union
from typing import Dict
from typing import Any


# Assuming we have a mapping of tags to their HTML versions
TAG_VERSIONS: Dict[str, str] = {
    # 'tag': 'version'
    "a": "HTML 2.0",
    "div": "HTML 3.2",
    # ... and so on for all other tags
}


# Define Pydantic models for HTML items
# class Text(BaseModel):
#     item: str

#     def __str__(self):
#         return escape(self.item)


class UnsafeRawText(BaseModel):
    item: str

    def __str__(self):
        return self.item


class Comment(BaseModel):
    contents: str

    def __str__(self):
        return f"<!--{escape(self.contents)}-->"


void_tags = set(
    [
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
    ]
)


# Pydantic model for attributes, allowing extra keys.
class Attributes(BaseModel):
    # Rest of the fields...
    html_version: Optional[str] = None

    class Config:
        extra = "allow"

    @root_validator(pre=True)
    def set_default_version(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        tag = values.get("__tag__")
        if tag and tag in TAG_VERSIONS:
            values["html_version"] = TAG_VERSIONS[tag]
        return values

    @validator("*")
    def escape_attributes(cls, v):
        return escape(str(v), quote=True)


class HtmlItem(BaseModel):
    pass


class Text(HtmlItem):
    content: str

    def __str__(self):
        return escape(self.content)


# class Tag(BaseModel):
#     tag: str
#     children: Optional[List[Union['Tag', Text, UnsafeRawText, Comment]]] = None
#     attrs: Optional[Attributes] = None
#     is_void: bool = Field(default=False)
#     html_version: Optional[str] = None

#     def __init__(self, **data):
#         super().__init__(**data)
#         self.is_void = self.tag in void_tags
#         if not self.html_version and self.tag in TAG_VERSIONS:
#             self.html_version = TAG_VERSIONS[self.tag]
#         if self.attrs:
#             self.attrs.__dict__['__tag__'] = self.tag


class Tag(HtmlItem):
    tag: str
    is_void: bool = Field(default=False)
    children: List[Union["Tag", Text]] = Field(default_factory=list)
    attrs: dict = Field(default_factory=dict)

    def __init__(__pydantic_self__, _tag: str, *children: Any, **attrs: Any):
        super().__init__(tag=_tag, attrs=attrs)
        __pydantic_self__.is_void = _tag in void_tags
        __pydantic_self__.children = []

        # Handle children passed as positional arguments
        for child in children:
            if isinstance(child, HtmlItem):
                __pydantic_self__.children.append(child)
            elif child is None:
                pass  # Allow None to make inline ifs easy
            else:
                __pydantic_self__.children.append(Text(content=str(child)))

    def __str__(self):
        attrs_str = " ".join(
            f'{k}="{v}"' for k, v in (self.attrs.dict().items() if self.attrs else [])
        )
        children_str = (
            "".join(str(child) for child in self.children) if self.children else ""
        )
        return (
            f"<{self.tag} {attrs_str}>"
            if self.is_void
            else children_str + f"</{self.tag}>"
        )


# Using Pydantic's `create_model` function to dynamically create tag classes
def tag_class(tag_name):
    is_void = tag_name in void_tags
    return create_model(
        tag_name, __base__=Tag, tag=(str, tag_name), is_void=(bool, is_void)
    )


# ... Include the rest of the class definitions from previous code ...


def html_to_objects(tag):
    """
    Recursively convert a BeautifulSoup tag into our custom html_item objects.
    """
    # If the tag is a string (i.e., text), return a text object
    if isinstance(tag, str):
        return text(tag)

    # Create the corresponding tag object
    tag_attrs = {key: value for key, value in tag.attrs.items()}
    tag_obj = tag_class(tag.name)(**tag_attrs)

    # Recursively process children
    children = [
        html_to_objects(child) for child in tag.contents if not isinstance(child, str)
    ]
    text_children = [text(child) for child in tag.contents if isinstance(child, str)]

    # Combine text and tag children
    tag_obj.children = text_children + children

    return tag_obj


def parse_html(html_content):
    """
    Parse HTML content and return the root html_item objects.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Assuming the HTML has a single root node or we just want to parse from the body
    body = soup.body
    if body:
        return html_to_objects(body)
    else:
        # If there's no body tag, we take the entire document
        return html_to_objects(soup)


# Now we use this function to create our tag models
A = tag_class("a")
Div = tag_class("div")
Span = tag_class("span")
H1 = tag_class("h1")
P = tag_class("p")
Img = tag_class("img")
Br = tag_class("br")


def main():
    # Example usage:
    # my_div = Tag('div', Text(content='Hello'), 'world')
    # my_div = Div(children=[Span(children=[Text(item="Hello, world!")])])
    # print(str(my_div))

    div_tag = Tag(
        "div",
        Text(content="Hello, World!"),
        Tag("span", Text(content="This is a test.")),
    )
    print(str(div_tag))

    # my_page = H1(
    #     children=[
    #         Text(item="Welcome to My Page"),
    #         P(children=[Text(item="This is a paragraph.")]),
    #         Img(attrs=Attributes(src="image.jpg")),
    #         Br(),
    #     ]
    # )

    # print(str(my_page))

    # # Usage example:
    # html_content = """
    # <!DOCTYPE html>
    # <html>
    # <head>
    #     <title>My Page</title>
    # </head>
    # <body>
    #     <h1>Welcome to My Page</h1>
    #     <p>This is a paragraph with <a href="#">a link</a>.</p>
    #     <img src="image.jpg" alt="A beautiful image.">
    # </body>
    # </html>
    # """

    # parsed_html = parse_html(html_content)
    # print(str(parsed_html))


if __name__ == "__main__":
    typer.run(main)
