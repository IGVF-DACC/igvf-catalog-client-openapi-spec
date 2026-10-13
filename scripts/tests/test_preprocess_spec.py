import json

from scripts import preprocess_spec, remove_endpoints


def iter_refs(node):
    if isinstance(node, dict):
        if "$ref" in node:
            yield node["$ref"]
        for v in node.values():
            yield from iter_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_refs(v)


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
    for ref in iter_refs(spec):
        _, _, kind, name = ref.split("/")
        assert name in spec["components"][kind], ref
    genes_200 = spec["paths"]["/genes"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert "$ref" in json.dumps(genes_200)


def test_is_deterministic(spec_file, tmp_path):
    _, out = run(spec_file, tmp_path)
    first = out.read_text()
    out2 = tmp_path / "processed2.json"
    preprocess_spec.main(["--input", str(spec_file), "--output", str(out2)])
    assert out2.read_text() == first
