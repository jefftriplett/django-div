"""Components used by the Django backend tests."""

from django_div import H1, Div, P, Span


def home(title, **context):
    return Div(H1(title), class_="page")


def greet(name="world"):
    """Takes only what it declares, ignoring the rest of the context."""
    return P(f"Hello, {name}")


def shows_request(request):
    return Span(request.path)


def returns_a_string():
    return "just text"


not_callable = "I am not a component"
