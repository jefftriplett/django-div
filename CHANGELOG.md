# Changelog

Versions are CalVer, `YYYY.M.N`: an unpadded month, and a micro that starts at
1 for each release within that month. Dates are UTC.

## Unreleased

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
