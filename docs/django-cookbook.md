# Django cookbook

Recipes for using django-div inside a Django project. Every example is
executed by `tests/test_cookbook.py`.

See [Django](django.md) for the template backend and escaping rules, and the
[Cookbook](cookbook.md) for recipes that don't need Django.

## Template tags

### A simple tag that returns markup

The most incremental way to adopt django-div: keep your templates, replace
one widget.

```python title="myapp/templatetags/ui.py"
from django import template
from django_div import Span

register = template.Library()


@register.simple_tag
def badge(text, tone="info"):
    return Span(text, class_=["badge", f"badge-{tone}"]).render()
```

```django
{% load ui %}
{% badge "New" tone="success" %}
```

```html
<span class="badge badge-success">New</span>
```

`.render()` returns a `SafeString`, so `simple_tag` won't escape it.

!!! tip "Inclusion tags without the template"

    `@register.inclusion_tag` exists to render a small template with a small
    context. A `simple_tag` returning a component does the same job with no
    second file and no template lookup.

### Passing a tag through the context

A view can build a component and hand it to an ordinary template. No `|safe`
is needed. See [escaping](django.md#escaping-both-directions).

```python
def dashboard(request):
    return render(request, "dashboard.html", {"card": Div(H2("Hi"), class_="card")})
```

```django
{{ card }}
```

```html
<div class="card"><h2>Hi</h2></div>
```

## Forms

### Render a field with its label and errors

```python
def render_field(field):
    return Div(
        Label(field.label, for_=field.id_for_label),
        Raw(content=str(field)),
        field.errors and Ul([Li(error) for error in field.errors], class_="errors"),
        class_="field",
    )
```

```html
<div class="field"><label for="id_email">Email</label><input type="email" name="email" ...><ul class="errors"><li>Enter a valid email address.</li></ul></div>
```

Two things are carrying the weight here:

- `Raw(content=str(field))` emits the widget's own markup untouched. You
  could also pass `field` directly, since Django's rendered widget carries
  `__html__`.
- `field.errors and ...` drops the whole list when there are no errors,
  because `False` children disappear.

### Add a CSS class to a widget

Rather than rebuilding the widget or editing `attrs` at form-definition
time, parse what Django produced and adjust it:

```python
def with_class(widget_html, css_class):
    tree = from_html(str(widget_html))
    existing = tree.attrs.get("class")
    tree.attrs["class"] = " ".join(filter(None, [existing, css_class]))
    return tree

with_class(form["email"], "form-control")
```

```html
<input type="email" name="email" ... class="form-control" />
```

This works on any widget, including third-party ones you don't control.

!!! note

    Boolean attributes come back from the parser with an empty value, so
    `required` re-renders as `required=""`. That's equivalent HTML, not a
    change in meaning.

### A form with CSRF

```python
from django_div.django import csrf_input

Form(csrf_input(request), Input(name="q"), Button("Go"), method="post")
```

```html
<form method="post"><input type="hidden" name="csrfmiddlewaretoken" value="..."><input name="q" /><button>Go</button></form>
```

## Views

### Respond without a template

```python
from django_div.django import as_response

def index(request):
    return as_response(Div(H1("Hi")))
```

`as_response()` forwards keyword arguments to `HttpResponse`, so
`status=404` and `content_type=` work as usual.

### htmx partials

htmx wants a fragment, which is exactly what a component already is. `hx_*`
attributes normalize to `hx-*`.

```python
def item_row(item):
    return Tr(
        Td(item["name"]),
        Td(Button("Delete",
                  hx_delete=f"/items/{item['id']}/",
                  hx_target="closest tr",
                  hx_swap="outerHTML")),
        id=f"item-{item['id']}",
    )


def delete_item(request, pk):
    Item.objects.filter(pk=pk).delete()
    return HttpResponse("")          # htmx swaps the row away
```

```html
<tr id="item-3"><td>Ana</td><td><button hx-delete="/items/3/" hx-target="closest tr" hx-swap="outerHTML">Delete</button></td></tr>
```

The same function serves the full page and the partial, so the two can't
drift apart.

## Components

### Messages

```python
def alerts(messages):
    return Div(
        [Div(message, class_=["alert", f"alert-{level}"]) for level, message in messages],
        class_="messages",
    )

alerts((m.level_tag, m.message) for m in get_messages(request))
```

```html
<div class="messages"><div class="alert alert-info">Saved</div></div>
```

### Pagination

```python
def pagination(number, num_pages, base="?page="):
    return Nav(
        Ul(
            Li(A("Previous", href=f"{base}{number - 1}")) if number > 1 else None,
            [Li(A(str(n), href=f"{base}{n}", class_={"current": n == number}))
             for n in range(1, num_pages + 1)],
            Li(A("Next", href=f"{base}{number + 1}")) if number < num_pages else None,
        ),
        class_="pagination",
    )

pagination(page_obj.number, page_obj.paginator.num_pages)
```

The `if ... else None` arms disappear on the first and last page, which in a
template would be two `{% if %}` blocks.

### Breadcrumbs

```python
def breadcrumbs(trail):
    items = []
    for index, (label, url) in enumerate(trail):
        last = index == len(trail) - 1
        items.append(Li(label if last else A(label, href=url), class_={"active": last}))
    return Nav(Ol(items, class_="breadcrumb"), aria_label="Breadcrumb")

breadcrumbs([("Home", "/"), ("Building", None)])
```

```html
<nav aria-label="Breadcrumb"><ol class="breadcrumb"><li><a href="/">Home</a></li><li class="active">Building</li></ol></nav>
```

## Passing data to JavaScript

`<script>` content is not escaped, and it can't be, or the code would break, so JSON has to be escaped for the *element*, not for HTML:

```python
import json

def json_script(data, id):
    return Script(json.dumps(data).replace("<", "\\u003C"),
                  id=id, type="application/json")

json_script({"a": "</script>"}, "config")
```

```html
<script id="config" type="application/json">{"a": "\u003C/script>"}</script>
```

`\u003C` is a valid JSON escape for `<`, so `JSON.parse()` returns the
original string while the literal `</script>` never appears in the document.

!!! danger "Never interpolate untrusted data into a Script"

    django-div refuses content containing the element's own closing tag, but
    that is a backstop, not a sanitizer. Pass data as JSON like this, or as a
    `data-` attribute, and read it from JavaScript. Django's own
    [`json_script`](https://docs.djangoproject.com/en/stable/ref/templates/builtins/#json-script)
    filter does the same job if you'd rather not hand-roll it.

## Email

HTML email wants a full document and inline styles:

```python
from django.core.mail import EmailMultiAlternatives

def receipt_email(order, to):
    html = render(document(
        "Receipt",
        P(f"Hi {order.customer}", style={"font_family": "sans-serif"}),
    ))
    message = EmailMultiAlternatives("Your receipt", strip_tags(html), to=[to])
    message.attach_alternative(html, "text/html")
    return message
```

`document()` and `render()` are from the
[Cookbook](cookbook.md#a-whole-document).

## Testing

### Assert on structure

```python
def test_search_page(client):
    page = from_html(client.get("/search/").content.decode())

    assert page.find("input", name="q") is not None
    assert [a.text for a in page.find_all("a", class_="result")] == ["First", "Second"]
```

Substring assertions break when markup is reformatted or an attribute is
reordered. Structural ones don't.

### Test a component directly

Components are functions returning values, so most of the time you don't
need a request, a client, or a database at all:

```python
def test_badge():
    assert str(badge("New", tone="success")) == (
        '<span class="badge badge-success">New</span>'
    )
```
