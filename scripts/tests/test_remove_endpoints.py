import json

from scripts import remove_endpoints


def test_clean_spec(fixture_spec):
    spec = remove_endpoints.clean_spec(fixture_spec)
    assert "/health" not in spec["paths"]
    assert "/autocomplete" not in spec["paths"]
    assert "/genes" in spec["paths"]
    aql = spec["paths"]["/llm-query"]["post"]["responses"]["200"]["content"][
        "application/json"]["schema"]["properties"]["aql_result"]
    assert aql["items"] == {}


def test_clean_spec_is_idempotent(fixture_spec):
    once = remove_endpoints.clean_spec(fixture_spec)
    snapshot = json.dumps(once, sort_keys=True)
    assert json.dumps(remove_endpoints.clean_spec(once), sort_keys=True) == snapshot


def test_main_in_place(spec_file):
    remove_endpoints.main(["--input", str(spec_file)])
    spec = json.loads(spec_file.read_text())
    assert "/health" not in spec["paths"]
    assert spec_file.read_text().endswith("}\n")


def test_main_output(spec_file, tmp_path):
    out = tmp_path / "out.json"
    before = spec_file.read_text()
    remove_endpoints.main(["--input", str(spec_file), "--output", str(out)])
    assert spec_file.read_text() == before
    assert "/health" not in json.loads(out.read_text())["paths"]
