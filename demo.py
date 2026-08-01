import typer

from bs4 import BeautifulSoup
from pydantic import BaseModel
from pydantic import Field
from rich import print
from typing import Optional, Dict, Type, Any


class Div(BaseModel):
    # Known attributes
    id: Optional[str] = Field(None, alias="id")
    name: Optional[str] = Field(None, alias="name")
    class_: Optional[str] = Field(None, alias="class")
    style: Optional[str] = Field(None, alias="style")

    # Capture all other attributes in a dictionary
    extra_attrs: Dict[str, Any] = Field(default_factory=dict)

    # Allow extra fields but process them separately
    class Config:
        extra = "allow"

    @classmethod
    def from_html(cls: Type["Div"], html: str) -> "Div":
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        if div:
            # Convert attributes to model fields format
            attrs = {attr.replace("-", "_"): value for attr, value in div.attrs.items()}
            # Handle 'class' attribute specifically if it's a list
            if "class" in attrs:
                attrs["class_"] = " ".join(attrs["class"])
                del attrs["class"]
            return cls(
                **attrs,
                extra_attrs={
                    key: value
                    for key, value in attrs.items()
                    if key not in cls.__fields__
                },
            )
        else:
            raise ValueError("No <div> element found in the input HTML.")

    def to_html(self) -> str:
        attrs = []
        for field_name, value in self.dict(exclude={"extra_attrs"}).items():
            if value is not None:
                # Handle special cases like class_ -> class
                field_name = "class" if field_name == "class_" else field_name
                attrs.append(f'{field_name}="{value}"')

        # Include extra attributes
        for attr, value in self.extra_attrs.items():
            attrs.append(f'{attr}="{value}"')

        return f'<div {" ".join(attrs)}></div>'


def main():
    # Example Usage
    # To read from a string with an arbitrary attribute
    html_str = '<div id="uniqueID" name="uniqueID" class="my-class" style="color: red;" data-custom="value"></div>'
    div_from_string = Div.from_html(html_str)
    # print(f"[yellow]{div_from_string}[/yellow]")

    # To output to a string
    print(div_from_string.to_html())


if __name__ == "__main__":
    typer.run(main)
