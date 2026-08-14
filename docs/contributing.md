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
| `just stub` | Regenerate `src/django_div/__init__.pyi` |
| `just install-hooks` | Install the prek git hooks |
| `just update-hooks` | Update pinned hook versions |
| `just build` | Build the sdist and the wheel into `dist/` |
| `just lock` | Refresh `uv.lock` |
| `just bump` | Raise the CalVer version and tag it |
| `just bump-dry` | The same, printed rather than applied |
| `just release` | Bump, relock, and push the tag |

```console
just test -k parse -x
```

## Layout

```
src/django_div/__init__.py   the library
src/django_div/__init__.pyi  generated type stub, see `just stub`
src/django_div/django.py     the Django integration
tests/test_django_div.py     core behavior
tests/test_tags.py           every tag, parametrized
tests/test_django.py         the Django integration
tests/components.py          components the Django tests render
examples/example.py          a runnable tour
docs/                        this site
```

## Conventions

**Alphabetical order.** Constants, then functions, then classes. Each group is
sorted, subject to Python needing base classes and helpers defined first.

**One positional argument.** Public functions take at most one positional
argument; everything else is keyword-only, enforced by
`test_public_functions_take_at_most_one_positional_argument`.

Tag constructors land in the same place differently: their positionals are
variadic children, so Python makes every named argument keyword-only, and the
generic `Tag` takes its element name positional-only. `test_tags.py` checks
the constructor shape of every element class.

**Comments explain why.** The what is in the code. Comments are for the
reason a thing is the way it is, usually a Pydantic or HTML constraint that
isn't obvious from reading.

## Tests

Every generated tag is covered by parametrized tests over `TAG_CLASSES`,
which check rendering empty and with attributes and children, category
behavior, and both round trips. Two tests compare the generated set against
the HTML living standard in both directions, so a missing or invented element
fails.

Adding an element means adding it to `_TAGS`. If it belongs to a category,
add it to `VOID_ELEMENTS`, `RAW_TEXT_ELEMENTS`, or `PRE_ELEMENTS` as well. The tests
will tell you. Then run `just stub`: the element classes are created at
runtime, which type checkers cannot see, so `src/django_div/__init__.pyi`
declares them all. `tests/test_stub.py` fails if the stub goes stale.

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
that means nothing outside the renderer (admonitions, grid cards, content
tabs), and a reader of the source would get raw `!!!` markers. Rendering first
turns them into prose.

The conversion itself is the library's own: each page goes through
`from_html()`-style parsing and `django_div.markdown.to_markdown()`, so every
docs build exercises both on real pages. The script only selects the
`<article>`, prunes navigation, permalink anchors, and icon SVGs, and
assembles `llms.txt`.

Page order comes from the `nav` in `zensical.toml`. A page missing from the
nav is appended alphabetically rather than dropped.

## CI

`.github/workflows/test.yml` runs pytest on Python 3.12, 3.13, 3.14, and
3.15, including the free-threaded builds `3.14t` and `3.15t`. The same file
runs lint.

Read the Docs builds and deploys the documentation. `.readthedocs.yaml`
configures it, and it runs the same `zensical build` plus `gen_llms.py` steps
as `just docs-build`.

## Releasing

Versions are CalVer, `YYYY.M.N`: an unpadded month, and a micro that starts
at 1 for each release within that month. `bumpver` owns the number, and its
configuration lives in `[tool.bumpver]`. It writes the version into
`pyproject.toml` and `src/django_div/__init__.py`, which a test compares.

Check what a bump would produce, then run it:

```console
just bump-dry
just release
```

`just release` bumps the version, commits, refreshes `uv.lock`, amends the
lock file into the same commit, re-creates the tag over it, and pushes the
commit with its tag.

The tag is what publishes. `.github/workflows/release.yml` matches a
`YYYY.M.N` tag, runs the tests, builds the sdist and the wheel, and uploads
them to PyPI.

There is no API token. PyPI uses **Trusted Publishing**: the workflow asks
GitHub for a short-lived OIDC token, and PyPI accepts it because the
repository, the workflow file, and the environment match what the project
declares. That is why the job carries `id-token: write` and runs in the
`pypi` environment.
