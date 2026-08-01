"""Tests for the Django integration."""

import pytest
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string
from django.test import RequestFactory
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy

from django_div import H1, Div, Form, P
from django_div.django import as_response, csrf_input, render_component


@pytest.fixture
def request_():
    return RequestFactory().get("/somewhere/")


# --- interop with Django's escaping and lazy objects ------------------------


def test_safestring_children_are_not_escaped():
    assert str(Div(mark_safe("<b>bold</b>"))) == "<div><b>bold</b></div>"


def test_unsafe_strings_are_still_escaped():
    assert str(Div("<b>bold</b>")) == "<div>&lt;b&gt;bold&lt;/b&gt;</div>"


def test_lazy_translations_render_as_one_string():
    # A lazy proxy is iterable, so a naive flatten yields one Text per char.
    assert str(Div(gettext_lazy("Hello & bye"))) == "<div>Hello &amp; bye</div>"


def test_render_returns_a_safestring():
    rendered = Div("hi").render()
    assert isinstance(rendered, SafeString)


def test_tags_are_safe_in_django_templates():
    from django.template import Context, Engine

    engine = Engine(libraries={})
    template = engine.from_string("{{ item }}")
    output = template.render(Context({"item": Div("a & b")}))
    assert output == "<div>a &amp; b</div>"


# --- view helpers -----------------------------------------------------------


def test_as_response():
    response = as_response(Div(H1("Hi")))
    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert response.content == b"<div><h1>Hi</h1></div>"


def test_as_response_passes_kwargs():
    response = as_response(Div("nope"), status=404, content_type="text/html")
    assert response.status_code == 404


def test_csrf_input(request_):
    form = Form(csrf_input(request_), method="post")
    rendered = str(form)
    assert rendered.startswith('<form method="post">')
    assert 'name="csrfmiddlewaretoken"' in rendered
    assert "&lt;input" not in rendered, "the token markup must not be escaped"


# --- the template backend ---------------------------------------------------


def test_get_template_resolves_a_dotted_path():
    template = get_template("tests.components.home")
    assert template.render({"title": "Hi"}) == '<div class="page"><h1>Hi</h1></div>'


def test_render_to_string():
    assert render_to_string("tests.components.greet", {"name": "Jeff"}) == (
        "<p>Hello, Jeff</p>"
    )


def test_component_only_receives_what_it_declares(request_):
    # 'request' is in the context but greet() does not accept it.
    assert render_to_string("tests.components.greet", request=request_) == (
        "<p>Hello, world</p>"
    )


def test_component_can_take_the_request(request_):
    assert render_to_string("tests.components.shows_request", request=request_) == (
        "<span>/somewhere/</span>"
    )


def test_context_processors_run(request_):
    template = get_template("tests.components.shows_request")
    assert "/somewhere/" in template.render({}, request=request_)


def test_rendered_output_is_safe():
    assert isinstance(render_to_string("tests.components.greet"), SafeString)


def test_component_returning_a_plain_string():
    assert render_to_string("tests.components.returns_a_string") == "just text"


def test_missing_module_raises_template_does_not_exist():
    with pytest.raises(TemplateDoesNotExist):
        get_template("tests.nope.missing")


def test_missing_attribute_raises_template_does_not_exist():
    with pytest.raises(TemplateDoesNotExist):
        get_template("tests.components.missing")


def test_bare_name_raises_template_does_not_exist():
    with pytest.raises(TemplateDoesNotExist):
        get_template("nodots")


def test_non_callable_raises_template_does_not_exist():
    with pytest.raises(TemplateDoesNotExist):
        get_template("tests.components.not_callable")


def test_from_string_is_refused():
    from django.template import engines

    with pytest.raises(NotImplementedError, match="dotted path"):
        engines["django_div"].from_string("<p>hi</p>")


def test_render_component_passes_everything_to_var_keyword():
    def component(**context):
        return P(str(sorted(context)))

    assert render_component(component, context={"b": 1, "a": 2}) == (
        "<p>[&#x27;a&#x27;, &#x27;b&#x27;]</p>"
    )
