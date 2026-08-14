"""Repository facts the docs state, checked against their real source.

The docs make claims about packaging, tooling, and CI that live outside the
library. Each one is cheap to check, so drift fails here rather than being
found by a reader.
"""

import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).parent.parent


def read(name):
    return (ROOT / name).read_text()


def test_documented_python_floor_matches_pyproject():
    """'Python 3.12 or later' tracks requires-python."""
    metadata = tomllib.loads(read("pyproject.toml"))
    floor = metadata["project"]["requires-python"].lstrip(">=")
    claim = f"needs Python {floor} or later"
    for name in ("docs/index.md", "README.md"):
        assert claim in read(name), name


def test_documented_just_recipes_match_the_justfile():
    """Every recipe is in the contributing table, and the table invents none."""
    # A recipe is a line-initial name, with or without just's @ quiet prefix.
    recipes = set(
        re.findall(r"^@?([a-z][\w-]*)[^:\n]*:", read("justfile"), re.MULTILINE)
    )
    recipes.discard("_default")
    page = read("docs/contributing.md")
    documented = set(re.findall(r"`just ([\w-]+)`", page))
    assert recipes - documented == set(), "undocumented recipes"
    assert documented - recipes == set(), "documented recipes that do not exist"


def test_documented_ci_python_versions_match_the_workflow():
    workflow = read(".github/workflows/test.yml")
    versions = re.search(r"python-version: \[(.+?)\]", workflow).group(1)
    page = read("docs/contributing.md")
    for version in re.findall(r'"([\d.t]+)"', versions):
        assert version in page, version


def test_documented_extras_match_pyproject():
    metadata = tomllib.loads(read("pyproject.toml"))
    extras = set(metadata["project"]["optional-dependencies"])
    for name in ("docs/index.md", "README.md"):
        page = read(name)
        for extra in extras:
            assert f"django-div[{extra}]" in page, f"{name}: {extra}"


def read_changelog_versions():
    """Version headings in CHANGELOG.md, newest first, as (version, date)."""
    body = read("CHANGELOG.md")
    return re.findall(r"^## (\d+\.\d+\.\d+) - (\d{4}-\d{2}-\d{2})$", body, re.MULTILINE)


def test_changelog_covers_the_current_version():
    """A bump without a changelog entry fails before the release publishes."""
    metadata = tomllib.loads(read("pyproject.toml"))
    version = metadata["project"]["version"]
    assert version in [v for v, _ in read_changelog_versions()], version


def test_changelog_keeps_an_unreleased_section():
    assert "\n## Unreleased\n" in read("CHANGELOG.md")


def test_changelog_versions_are_newest_first():
    versions = [
        tuple(int(part) for part in v.split(".")) for v, _ in read_changelog_versions()
    ]
    assert versions == sorted(versions, reverse=True)
