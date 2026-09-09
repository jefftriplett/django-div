"""Browser data must remain valid JSON without escaping its script element."""

import json
from datetime import date

import pytest
from pydantic import BaseModel, Field

from django_div import Div, JsonScript, Script, Tag, from_html


def test_json_script_preserves_data():
    data = {
        "text": "</ScRiPt><script>alert(1)</script><!--&>\u2028\u2029é",
        "null": None,
        "items": [True, False, 42],
    }
    item = JsonScript(data, id="config")
    assert isinstance(item, Script)
    assert str(item).startswith('<script type="application/json" id="config">')
    assert "<" not in item.text
    assert "&" not in item.text
    assert json.loads(item.text) == data
    assert json.loads(from_html(str(item)).text) == data


def test_nested_models_preserve_nulls_aliases_and_json_types():
    class Settings(BaseModel):
        name: str | None = Field(None, alias="displayName")
        day: date = date(2026, 9, 9)

    item = JsonScript({"settings": [Settings()], "missing": None})
    assert json.loads(item.text) == {
        "settings": [{"displayName": None, "day": "2026-09-09"}],
        "missing": None,
    }
    assert JsonScript().text == "null"


def test_json_script_round_trips():
    item = JsonScript({"value": None}, id="config")
    tree = Div(item)
    restored = Tag.model_validate_json(tree.model_dump_json())
    assert type(restored.children[0]) is Script
    assert str(restored) == str(tree)
    assert str(JsonScript.model_validate_json(item.model_dump_json())) == str(item)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_json_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        JsonScript({"value": value})


def test_unsupported_values_are_rejected():
    with pytest.raises(TypeError):
        JsonScript(object())
