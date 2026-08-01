# Django

Django is optional. Only `django_div.django` imports it, so installing
django-div in a non-Django project pulls in nothing.

## Escaping, both directions

Rendering escapes text and attribute values, so output is safe markup by
construction. A tag can go straight into a template context with no `|safe`:

```django
{{ card }}
```

!!! info "Why `__html__` alone wasn't enough"

    Django's template engine calls `str()` on any value that isn't already a
    string *before* it looks for `__html__`. A plain `str` return would have
    been escaped, so `__str__` itself reports the result as safe.

Interop runs the other way too. Anything carrying `__html__` — a
`SafeString`, a `markupsafe.Markup`, a rendered form — passes through a tag
unescaped, while ordinary strings are still escaped:

```python
Div(mark_safe("<b>bold</b>"))   # <div><b>bold</b></div>
Div("<b>bold</b>")              # <div>&lt;b&gt;bold&lt;/b&gt;</div>
Div(form.as_p())                # the form's own markup, intact
```

Lazy objects resolve correctly, so translations work:

```python
Div(gettext_lazy("Hello"))      # <div>Hello</div>
```

## Components as templates

`DjangoDivTemplates` is a template backend whose templates are Python
callables. Register it alongside your existing engines:

```python title="settings.py"
TEMPLATES = [
    {
        "BACKEND": "django_div.django.DjangoDivTemplates",
        "NAME": "django_div",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # ... your usual configuration, untouched
    },
]
```

A component is any callable returning an `HtmlItem`, addressed by its dotted
path:

```python title="myapp/components.py"
from django_div import H1, Div, Li, P, Ul


def home(title, items, **context):
    return Div(
        H1(title),
        Ul(Li(item) for item in items),
        class_="page",
    )
```

```python title="myapp/views.py"
from django.shortcuts import render


def home_view(request):
    return render(request, "myapp.components.home", {
        "title": "Hi",
        "items": ["one", "two"],
    })
```

Because it is a normal backend, `render()`, `render_to_string()`,
`get_template()`, and the generic class-based views all work unchanged.

### Context handling

A component receives the context as keyword arguments:

- Declare `**kwargs` and you get the whole context.
- Name your parameters and you get only those.

```python
def greet(name="world"):        # ignores request, user, csrf_token, ...
    return P(f"Hello, {name}")
```

That second case matters. Context processors add `request`, `user`, `perms`,
and more to every render; without the filtering, adding one would break every
component signature at once.

### Incremental adoption

A component that can't be resolved raises `TemplateDoesNotExist`, so Django's
loader falls through to the next engine. Ordinary `.html` templates keep
working, and you can convert one view at a time.

!!! warning "Template names are import paths"

    `"myapp.components.home"` is imported and called. Never build a template
    name from user input — that is an arbitrary-import primitive.

## Without the template layer

For views that build their own markup:

```python
from django_div import H1, Div, Form, Input
from django_div.django import as_response, csrf_input


def index(request):
    return as_response(Div(H1("Hi")))


def search(request):
    return as_response(
        Form(
            csrf_input(request),
            Input(name="q", placeholder="Search"),
            method="post",
        )
    )
```

`as_response()` passes extra keyword arguments to `HttpResponse`, so
`status=` and `content_type=` work as usual.

`csrf_input()` produces the hidden token field using Django's own machinery,
so it stays correct if that changes.

## Rendering a tag yourself

`render()` returns a `SafeString` when Django is installed, and a plain `str`
otherwise:

```python
Div("hi").render()
```

## What this is not

django-div does not replace Django's template language, and does not try to.
There is no inheritance, no `{% block %}`, and no partial loading — a
component is a function, so composition is function calls and default
arguments instead.

If you want template inheritance, keep those pages in Django templates and
use django-div for the parts that benefit from being Python.
