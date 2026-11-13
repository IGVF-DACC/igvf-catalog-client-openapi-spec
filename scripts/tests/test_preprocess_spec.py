import json
import re

import pytest

from scripts import preprocess_spec, remove_endpoints

ERROR_SCHEMAS = ["ErrorBadRequest", "ErrorUnauthorized", "ErrorForbidden",
                 "ErrorNotFound", "ErrorInternalServerError"]


def iter_refs(node):
    if isinstance(node, dict):
        if "$ref" in node:
            yield node["$ref"]
        for v in node.values():
            yield from iter_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_refs(v)


def assert_refs_resolve(spec):
    for ref in iter_refs(spec):
        _, _, kind, name = ref.split("/")
        assert name in spec["components"][kind], ref


def run(spec_file, tmp_path):
    remove_endpoints.main(["--input", str(spec_file)])
    out = tmp_path / "processed.json"
    rc = preprocess_spec.main(["--input", str(spec_file), "--output", str(out)])
    return rc, out


def test_extracts_schemas(spec_file, tmp_path):
    rc, out = run(spec_file, tmp_path)
    assert rc == 0
    spec = json.loads(out.read_text())
    schemas = spec["components"]["schemas"]
    assert schemas
    assert "Gene" in schemas
    assert_refs_resolve(spec)
    genes_200 = spec["paths"]["/genes"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert "$ref" in json.dumps(genes_200)


def test_is_deterministic(spec_file, tmp_path):
    _, out = run(spec_file, tmp_path)
    first = out.read_text()
    out2 = tmp_path / "processed2.json"
    preprocess_spec.main(["--input", str(spec_file), "--output", str(out2)])
    assert out2.read_text() == first


def test_keeps_and_renames_error_schemas(new_spec_file, tmp_path):
    rc, out = run(new_spec_file, tmp_path)
    assert rc == 0
    spec = json.loads(out.read_text())
    schemas = spec["components"]["schemas"]
    for name in ERROR_SCHEMAS + ["ErrorIssue"]:
        assert name in schemas, name
    for name in schemas:
        assert re.fullmatch(r"[A-Z][A-Za-z0-9]*", name), name
    assert_refs_resolve(spec)
    assert schemas["ErrorBadRequest"]["properties"]["issues"]["items"] == {
        "$ref": "#/components/schemas/ErrorIssue"}
    responses = spec["paths"]["/genes"]["get"]["responses"]
    assert responses["400"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorBadRequest"}


def test_keeps_referenced_component_schema(tmp_path):
    # The root cause of the failure after igvf-catalog PR #956: main() used to
    # replace components.schemas with only the schemas it had extracted.
    thing = {"type": "object", "properties": {"reason": {"type": "string"}}}
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "t", "version": "1"},
        "paths": {"/things": {"get": {
            "operationId": "things",
            "responses": {
                "200": {"description": "ok", "content": {"application/json": {"schema": {
                    "type": "object", "properties": {"name": {"type": "string"}}}}}},
                "400": {"description": "bad", "content": {"application/json": {"schema": {
                    "$ref": "#/components/schemas/Thing"}}}},
            },
        }}},
        "components": {"schemas": {"Thing": thing}},
    }
    src = tmp_path / "in.json"
    src.write_text(json.dumps(spec))
    out = tmp_path / "out.json"
    assert preprocess_spec.main(["--input", str(src), "--output", str(out)]) == 0
    processed = json.loads(out.read_text())
    assert processed["components"]["schemas"]["Thing"] == thing
    assert set(processed["components"]["schemas"]) == {"Thing", "Things"}
    assert_refs_resolve(processed)


@pytest.mark.parametrize("name, expected", [
    ("error.BAD_REQUEST", "ErrorBadRequest"),
    ("error.INTERNAL_SERVER_ERROR", "ErrorInternalServerError"),
    ("Gene", "Gene"),
    ("fooBar", "FooBar"),
])
def test_component_name(name, expected):
    assert preprocess_spec.component_name(name) == expected


def test_rename_existing_components_rewrites_refs():
    spec = {
        "paths": {"/x": {"get": {"responses": {"400": {"content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/error.BAD_REQUEST"}}}}}}}},
        "components": {"schemas": {"error.BAD_REQUEST": {"type": "object"}, "Gene": {"type": "object"}}},
    }
    assert preprocess_spec.rename_existing_components(spec) == {"ErrorBadRequest", "Gene"}
    assert list(spec["components"]["schemas"]) == ["ErrorBadRequest", "Gene"]
    assert list(iter_refs(spec)) == ["#/components/schemas/ErrorBadRequest"]


def test_rename_existing_components_without_components():
    spec = {"paths": {}}
    assert preprocess_spec.rename_existing_components(spec) == set()
    assert spec == {"paths": {}}


def test_rename_existing_components_collision():
    spec = {"paths": {}, "components": {"schemas": {
        "error.BAD_REQUEST": {"type": "object"}, "error.bad-request": {"type": "object"}}}}
    with pytest.raises(SystemExit, match="collide"):
        preprocess_spec.rename_existing_components(spec)
