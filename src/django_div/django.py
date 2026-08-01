"""Django integration: components as templates, plus view helpers.

Register the backend alongside your usual template engines::

    TEMPLATES = [
        {"BACKEND": "django_div.django.DjangoDivTemplates", "OPTIONS": {}},
        {"BACKEND": "django.template.backends.django.DjangoTemplates", ...},
    ]

Then a component is any callable returning an HtmlItem, addressed by its
dotted path, and ordinary Django views render it::

    # myapp/components.py
    def home(title, **context):
        return Div(H1(title), class_="page")

    # myapp/views.py
    def home_view(request):
        return render(request, "myapp.components.home", {"title": "Hi"})

Nothing here is imported by ``django_div`` itself, so Django stays optional.
"""

from __future__ import annotations

import inspect
from importlib import import_module
from typing import Any

from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.template.backends.base import BaseEngine
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe

from django_div import HtmlItem, Raw

__all__ = [
    "Component",
    "DjangoDivTemplates",
    "as_response",
    "csrf_input",
    "render_component",
]

#: A component is any callable that returns something renderable.
Component = Any


def as_response(item: HtmlItem, **kwargs: Any) -> HttpResponse:
    """Render an item straight into an HttpResponse.

    For views that build their own markup and skip the template layer::

        def index(request):
            return as_response(Div(H1("Hi")))
    """
    return HttpResponse(item.render(), **kwargs)


def csrf_input(request: Any) -> Raw:
    """The hidden CSRF field, for use inside a Form(...).

    Django's own token machinery produces the markup, so this stays correct
    if that changes.
    """
    from django.template.context_processors import csrf
    from django.utils.html import format_html

    token = csrf(request)["csrf_token"]
    return Raw(
        content=str(
            format_html(
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">',
                token,
            )
        )
    )


def render_component(component: Component, *, context: dict[str, Any]) -> str:
    """Call a component with the parts of the context it asks for.

    A component declaring ``**kwargs`` receives the whole context; one that
    names its parameters receives only those, so Django's context
    processors can add ``user``, ``perms``, and friends without breaking
    every component signature.
    """
    try:
        signature = inspect.signature(component)
    except (TypeError, ValueError):  # pragma: no cover - builtins, C callables
        return str(component(**context))

    takes_everything = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    if takes_everything:
        accepted = context
    else:
        accepted = {
            name: value
            for name, value in context.items()
            if name in signature.parameters
        }

    result = component(**accepted)
    return result.render() if isinstance(result, HtmlItem) else str(result)


class Template:
    """Adapts a component to the template object Django expects back."""

    def __init__(self, component: Component, backend: DjangoDivTemplates) -> None:
        self.component = component
        self.backend = backend
        self.origin = getattr(component, "__module__", "django_div")

    def render(self, context: dict[str, Any] | None = None, request: Any = None) -> str:
        context = dict(context or {})
        if request is not None:
            context.setdefault("request", request)
            for processor in self.backend.context_processors:
                context.update(processor(request))
        return mark_safe(render_component(self.component, context=context))


class DjangoDivTemplates(BaseEngine):
    """A template backend whose templates are Python callables.

    Template names are dotted paths to a component, so
    ``render(request, "myapp.components.home")`` calls ``home()`` and
    renders what it returns.
    """

    # Where Django's app-dirs machinery would look; unused, since components
    # are addressed by import path rather than by file.
    app_dirname = "components"

    def __init__(self, params: dict[str, Any]) -> None:
        params = params.copy()
        options = params.pop("OPTIONS").copy()
        self.context_processors = [
            import_string(path) for path in options.pop("context_processors", [])
        ]
        if options:
            raise ValueError(f"Unknown options: {', '.join(sorted(options))}")
        super().__init__(params)

    def from_string(self, template_code: str) -> Template:
        raise NotImplementedError(
            "django_div components are Python callables, not template source; "
            "reference one by its dotted path instead"
        )

    def get_template(self, template_name: str) -> Template:
        module_path, _, attribute = template_name.rpartition(".")
        if not module_path:
            raise TemplateDoesNotExist(template_name, backend=self)
        try:
            component = getattr(import_module(module_path), attribute)
        except (ImportError, AttributeError) as exc:
            raise TemplateDoesNotExist(template_name, backend=self) from exc
        if not callable(component):
            raise TemplateDoesNotExist(template_name, backend=self)
        return Template(component, self)
