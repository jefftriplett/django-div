# Contributing

## Setup

```console
git clone git@github.com:jefftriplett/django-div.git
cd django-div
just bootstrap
just install-hooks
```

`just bootstrap` runs `uv sync`, which installs the package plus the dev
group: pytest, ruff, prek, Django, and both parser backends.

## Commands

| Command | What it does |
| --- | --- |
| `just test` | Run pytest; extra arguments pass through |
| `just lint` | Run every hook over every file |
| `just ruff` | Just ruff, check and format |
| `just docs` | Serve the docs with live reload |
| `just docs-build` | Build the docs into `site/`, plus llms.txt |
| `just example` | Run `examples/example.py` |
| `just install-hooks` | Install the prek git hooks |
| `just update-hooks` | Update pinned hook versions |

```console
just test -k parse -x
```

## Layout

```
src/django_div/__init__.py   the library
src/django_div/django.py     the Django integration
tests/test_django_div.py     core behavior
tests/test_tags.py           every tag, parametrized
tests/test_django.py         the Django integration
tests/components.py          components the Django tests render
examples/example.py          a runnable tour
docs/                        this site
```

## Conventions

**Alphabetical order.** Constants, then functions, then classes — each group
sorted, subject to Python needing base classes and helpers defined first.

**One positional argument.** Public functions take at most one positional
argument; everything else is keyword-only, enforced by
`test_public_functions_take_at_most_one_positional_argument`.

Tag constructors land in the same place differently: their positionals are
variadic children, so Python makes every named argument keyword-only, and the
generic `Tag` takes its element name positional-only. `test_tags.py` checks
the constructor shape of every element class.

**Comments explain why.** The what is in the code. Comments are for the
reason a thing is the way it is — usually a Pydantic or HTML constraint that
isn't obvious from reading.

## Tests

Every generated tag is covered by parametrized tests over `TAG_CLASSES`,
which check rendering empty and with attributes and children, category
behavior, and both round trips. Two tests compare the generated set against
the HTML living standard in both directions, so a missing or invented element
fails.

Adding an element means adding it to `_TAGS`. If it belongs to a category,
add it to `VOID_ELEMENTS`, `RAW_TEXT_ELEMENTS`, or `PRE_ELEMENTS` as well — the tests
will tell you.

Deprecation warnings are errors:

```toml
filterwarnings = ["error::DeprecationWarning"]
```

So a Pydantic or Django deprecation fails the suite rather than scrolling
past.

## llms.txt

`scripts/gen_llms.py` runs after `zensical build` and writes `llms.txt`,
`llms-full.txt`, and a Markdown twin next to every page. Zensical has no
plugin API yet, so it is a post-build step rather than a plugin.

It reads the **rendered HTML**, not `docs/*.md`. The docs use Zensical syntax
that means nothing outside the renderer — admonitions, grid cards, content
tabs — and a reader of the source would get raw `!!!` markers. Rendering first
turns them into prose, and tables and definition lists are rebuilt as proper
Markdown on the way out.

Page order comes from the `nav` in `zensical.toml`. A page missing from the
nav is appended alphabetically rather than dropped.

## CI

`.github/workflows/test.yml` runs pytest on Python 3.10 through 3.14 plus
lint. `.github/workflows/docs.yml` builds and deploys the docs on pushes to
`main`.
