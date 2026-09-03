import json
import jsonschema
import pytest
from pathlib import Path

def get_schemas(dir_path):
    return list(Path(dir_path).rglob("*.schema.json")) + list(Path(dir_path).rglob("*.agent-spec.json"))

def get_fixtures(schema_path):
    schema_name = schema_path.name
    base_name = schema_name.split(".schema.json")[0] if ".schema.json" in schema_name else schema_name.split(".agent-spec.json")[0]

    fixtures_dir = schema_path.parent / "fixtures"
    valid_fixtures = list(fixtures_dir.glob(f"*{base_name}*valid*.json"))
    valid_fixtures = [f for f in valid_fixtures if "invalid" not in f.name]
    invalid_fixtures = list(fixtures_dir.glob(f"*{base_name}*invalid*.json"))

    return valid_fixtures, invalid_fixtures


def test_all_schemas():
    schemas = get_schemas("schemas") + get_schemas("agents")
    for schema_path in schemas:
        schema = json.load(open(schema_path))
        valid_fixtures, invalid_fixtures = get_fixtures(schema_path)

        for fixture_path in valid_fixtures:
            fixture = json.load(open(fixture_path))
            jsonschema.validate(instance=fixture, schema=schema)

        for fixture_path in invalid_fixtures:
            fixture = json.load(open(fixture_path))
            with pytest.raises(jsonschema.exceptions.ValidationError):
                jsonschema.validate(instance=fixture, schema=schema)
