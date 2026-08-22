# Changelog

Versions are CalVer, `YYYY.M.N`: an unpadded month, and a micro that starts at
1 for each release within that month. Dates are UTC.

## Unreleased

## 2026.8.3 - 2026-08-22

### Added

- The 20 elements MDN's browser-compat-data tracks that were missing: 18
  deprecated (`acronym`, `big`, `center`, `dir`, `fencedframe`, `font`,
  `frame`, `frameset`, `marquee`, `nobr`, `noembed`, `noframes`, `plaintext`,
  `rb`, `rtc`, `strike`, `tt`, `xmp`) and 2 experimental (`geolocation`,
  `model`). 134 elements now, up from 114.
- `DeprecatedElementWarning` and `ExperimentalElementWarning`, raised when
  markup is authored -- never when it is parsed or deserialized, so reading a
  legacy document stays quiet. `DeprecatedElementWarning` subclasses
  `DeprecationWarning`, so Python's stock filters already hide it in
  application code and surface it under pytest and `python -W`.
  `ExperimentalElementWarning` is filtered out on import; the filter is
  appended, so `-W` and any `filterwarnings` call still reach it.
- `DEPRECATED_ELEMENTS` and `EXPERIMENTAL_ELEMENTS`, for finding these
  elements by grep rather than by warning.
- `JsonLd(data, **attrs)`, a `Script` holding any Pydantic model, dict, or
  list as JSON-LD. Models are dumped by alias, since `@context` and `@type`
  can only be declared as aliases, and with `None` dropped. `None` fields drop out, since a JSON-LD null is not a value.
  The JSON is escaped per `JSON_LD_ESCAPES` so no string in it can end the
  script element or open an HTML comment: a `<script>` is raw text, so a
  description containing `</script>` would otherwise close the tag early and
  leave the rest of the payload on the page as live markup.
- `render_json_ld(data)` and `as_json(value)`, the serializer and the
  `json.dumps(..., default=...)` hook behind them, which reach nested models
  too.

### Changed

- `param` moved into `DEPRECATED_ELEMENTS`, so `Param(...)` now warns. It was
  already documented as obsolete; MDN marks it deprecated too.
- `frame` is a void element, so `Frame()` renders `<frame />`.

## 2026.8.2 - 2026-08-14

### Changed

- The license is now BSD 3-Clause, the same one Django uses. Releases up to and
  including 2026.8.1 went out under MIT.

### Fixed

- The `LICENSE` file now ships inside the wheel and the sdist. `license-files`
  was missing, so 2026.8.1 carries the license expression in its metadata but
  not the license text.

## 2026.8.1 - 2026-08-14

The first release on PyPI.

### Added

- `Tag`, `Text`, `Raw`, `Comment`, and `Doctype`, all Pydantic models, plus a
  generated class for every one of the 114 elements in the HTML living
  standard.
- Escaping by default for text children and attribute values, with `Raw` and
  the `__html__` protocol as the ways to pass trusted markup through.
- Enforced element categories: void elements refuse children, raw text
  elements skip escaping, and `pre` keeps its whitespace.
- `parse()` and `from_html()` over BeautifulSoup, with `find()`, `find_all()`,
  `iter_find()`, and `walk()` on the resulting tree.
- JSON round trips through `model_dump()` and `model_validate()`, which
  restore the original element classes.
- `django_div.markdown`, with `to_markdown()` needing no dependency and
  `from_markdown()` reading through markdown-it-py.
- `django_div.django`: a template backend that treats components as templates,
  `as_response()`, and `csrf_input()`.
- Publishing through PyPI Trusted Publishing, with no API token.
