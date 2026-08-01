"""The committed type stub stays in sync with the live module.

The element classes are created at runtime, so type checkers only know the
names src/django_div/__init__.pyi declares. Same pattern as the element-count
guard in test_tags.py: changing the public API without regenerating the stub
fails here rather than shipping a stale stub.
"""

import ast
from pathlib import Path

import django_div
from scripts.gen_stub import build_stub

STUB = Path(__file__).parent.parent / "src" / "django_div" / "__init__.pyi"


def stub_tree() -> ast.Module:
    return ast.parse(STUB.read_text())


def test_stub_matches_generator():
    """Regenerate with `just stub` when this fails."""
    assert STUB.read_text() == build_stub()


def test_stub_declares_every_element_class():
    classes = {node.name for node in stub_tree().body if isinstance(node, ast.ClassDef)}
    for tag in django_div.BUILTIN_TAGS:
        assert django_div.TAG_CLASSES[tag].__name__ in classes


def test_stub_all_matches_runtime_all():
    module = ast.parse(STUB.read_text())
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        ):
            stub_all = {constant.value for constant in node.value.elts}
            break
    else:
        raise AssertionError("stub has no __all__")
    assert stub_all == set(django_div.__all__)
