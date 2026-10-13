#!/usr/bin/env python3
"""Extract inline schemas from OpenAPI spec into components/schemas.

Reads the --input spec, extracts all inline object schemas into
components/schemas with short domain-meaningful names, and writes
the result to --output.

This produces much shorter model names when used with openapi-generator-cli.
"""

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict

PATHS_TO_REMOVE = []

SEMANTIC_NAMES = {
    frozenset(["_id", "alt", "ca_id", "chr", "hgvs", "pos", "ref", "rsid",
               "spdi"]): "VariantBasic",
    frozenset(["class", "description", "files_filesets", "method", "name",
               "source", "source_url", "subontology", "synonyms", "term_id",
               "uri"]): "OntologyTerm",
    frozenset(["_id", "chr", "collections", "end", "entrez", "gene_type",
               "hgnc", "name", "source", "source_url", "start", "strand",
               "study_sets", "synonyms", "version"]): "Gene",
    frozenset(["id", "name"]): "IdName",
    frozenset(["MANE_Select", "_id", "dbxrefs", "name", "organism", "source",
               "source_url", "uniprot_full_names", "uniprot_ids",
               "uniprot_names"]): "Protein",
    frozenset(["_id", "alt", "annotations", "ca_id", "chr", "files_filesets",
               "hgvs", "organism", "pos", "qual", "ref", "rsid", "source",
               "source_url", "spdi", "strain"]): "SequenceVariant",
    frozenset(["GENCODE_category", "bravo_af", "funseq_description",
               "gnomad_af_afr", "gnomad_af_afr_female", "gnomad_af_afr_male",
               "gnomad_af_ami", "gnomad_af_ami_female", "gnomad_af_ami_male",
               "gnomad_af_amr", "gnomad_af_amr_female", "gnomad_af_amr_male",
               "gnomad_af_asj", "gnomad_af_asj_female", "gnomad_af_asj_male",
               "gnomad_af_eas", "gnomad_af_eas_female", "gnomad_af_eas_male",
               "gnomad_af_female", "gnomad_af_fin", "gnomad_af_fin_female",
               "gnomad_af_fin_male", "gnomad_af_male", "gnomad_af_nfe",
               "gnomad_af_nfe_female", "gnomad_af_nfe_male", "gnomad_af_oth",
               "gnomad_af_oth_female", "gnomad_af_oth_male", "gnomad_af_raw",
               "gnomad_af_sas", "gnomad_af_sas_female", "gnomad_af_sas_male",
               "gnomad_af_total"]): "VariantAnnotations",
    frozenset(["_id", "alias", "class", "complex_assembly", "complex_source",
               "description", "evidence_code", "experimental_evidence",
               "files_filesets", "label", "method", "molecules", "name",
               "reactome_xref", "source", "source_url"]): "Complex",
    frozenset(["_id", "ancestry_initial", "ancestry_replication",
               "files_filesets", "has_sumstats", "n_cases", "n_initial",
               "n_replication", "name", "num_assoc_loci", "pmid",
               "pub_author", "pub_date", "pub_journal", "pub_title", "source",
               "study_source", "study_type", "trait_category", "trait_efos",
               "trait_reported", "version"]): "Study",
    frozenset(["_id", "class", "disease_ontology_terms", "files_filesets",
               "go_biological_process", "id_version", "is_in_disease",
               "is_top_level_pathway", "label", "method", "name",
               "name_aliases", "organism", "source",
               "source_url"]): "Pathway",
    frozenset(["MANE_Select", "_id", "chr", "end", "gene_name", "name",
               "source", "source_url", "start", "strand", "transcript_type",
               "version"]): "Transcript",
    frozenset(["MANE_Select", "_id", "name", "organism", "source",
               "source_url", "uniprot_full_names", "uniprot_ids",
               "uniprot_names"]): "ProteinBasic",
    frozenset(["_id", "chr", "end", "name", "source", "source_annotation",
               "source_url", "start", "type"]): "GenomicElement",
    frozenset(["_id", "chr", "files_filesets", "gene_id", "hgnc", "name",
               "organism"]): "GeneCompact",
    frozenset(["_id", "files_filesets", "name",
               "uniprot_names"]): "ProteinCompact",
    frozenset(["phenotype_id", "phenotype_name"]): "PhenotypeRef",
    frozenset(["_id", "chr", "end", "name", "start",
               "type"]): "GenomicElementBasic",
    frozenset(["_id", "chr", "end", "name", "start"]): "GeneRef",
    frozenset(["class", "files_filesets", "length", "method", "name", "pwm",
               "source", "source_url", "tf_name"]): "Motif",
    frozenset(["chr", "end", "method", "name", "source", "source_annotation",
               "source_url", "start", "strand",
               "type"]): "GenomicElementFull",
    frozenset(["_id", "class", "drug_ontology_terms", "files_filesets",
               "method", "name", "source", "source_url"]): "Drug",
    frozenset(["_id", "aapos", "alt", "gene_name", "hgvsp", "protein_name",
               "ref"]): "CodingVariant",
    frozenset(["_id", "chr", "collections", "end", "entrez", "gene_type",
               "hgnc", "name", "source", "source_url", "start", "strand",
               "study_sets", "version"]): "GeneNoSynonyms",
    frozenset(["participantId", "ranges"]): "LinkedFeature",
    frozenset(["count", "method"]): "MethodCount",
    frozenset(["class", "description", "files_filesets", "method", "name",
               "source", "subontology", "synonyms", "term_id",
               "uri"]): "OntologyTermBasic",
    frozenset(["biogeographical_groups", "p-value", "study_cases",
               "study_controls", "study_parameter_id",
               "study_type"]): "StudyParameters",
    frozenset(["distance", "end", "gene_name", "id",
               "start"]): "NearestGene",
    frozenset(["alt", "ca_id", "chr", "hgvs", "pos", "ref", "rsid",
               "spdi"]): "VariantRef",
    frozenset(["alt", "chr", "hgvs", "pos", "ref", "rsid",
               "spdi"]): "VariantMinimal",
}


def fingerprint(schema, depth=0):
    """Structural fingerprint of a schema, including nullable but excluding
    description, required, and additionalProperties (boolean form)."""
    if depth > 20:
        return "MAX_DEPTH"
    if not isinstance(schema, dict):
        return str(schema)
    if "$ref" in schema:
        return f"$ref({schema['$ref']})"
    if "anyOf" in schema:
        parts = sorted(fingerprint(v, depth + 1) for v in schema["anyOf"])
        r = f"anyOf({','.join(parts)})"
        if schema.get("nullable"):
            r += "?"
        return r
    if "not" in schema:
        return f"not({fingerprint(schema['not'], depth + 1)})"
    t = schema.get("type")
    if t == "object" and "properties" in schema:
        pf = {
            n: fingerprint(schema["properties"][n], depth + 1)
            for n in sorted(schema["properties"])
        }
        return f"obj({json.dumps(pf, sort_keys=True)})"
    if t == "array":
        return f"arr({fingerprint(schema.get('items', {}), depth + 1)})"
    if t:
        n = "?" if schema.get("nullable") else ""
        e = ""
        if "enum" in schema:
            e = f"[{','.join(str(v) for v in schema['enum'])}]"
        return f"{t}{n}{e}"
    if isinstance(schema.get("additionalProperties"), dict):
        return f"map({fingerprint(schema['additionalProperties'], depth + 1)})"
    return "any"


def walk_and_collect(spec):
    """Walk all paths and collect inline object schemas with their locations."""
    locations = []

    def walk(node, path, depth, op_id, field_name):
        if not isinstance(node, dict) or "$ref" in node:
            return
        if node.get("type") == "object" and "properties" in node:
            fp = fingerprint(node)
            props = tuple(sorted(node["properties"].keys()))
            locations.append({
                "json_path": list(path),
                "field_name": field_name,
                "depth": depth,
                "op_id": op_id,
                "fingerprint": fp,
                "prop_names": props,
            })
            for pname in sorted(node["properties"]):
                walk(node["properties"][pname],
                     path + ("properties", pname), depth + 1, op_id, pname)
            ap = node.get("additionalProperties")
            if isinstance(ap, dict):
                walk(ap, path + ("additionalProperties",),
                     depth + 1, op_id, field_name)
            return

        if "anyOf" in node:
            for i, variant in enumerate(node["anyOf"]):
                walk(variant, path + ("anyOf", i), depth, op_id, field_name)
        if "items" in node and isinstance(node["items"], dict):
            walk(node["items"], path + ("items",), depth + 1, op_id,
                 field_name)
        ap = node.get("additionalProperties")
        if isinstance(ap, dict):
            walk(ap, path + ("additionalProperties",),
                 depth + 1, op_id, field_name)

    for api_path in sorted(spec.get("paths", {})):
        methods = spec["paths"][api_path]
        for method_name in ("get", "post", "put", "patch", "delete"):
            if method_name not in methods:
                continue
            op = methods[method_name]
            op_id = op.get("operationId", api_path)
            resp_schema = (
                op.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            if resp_schema:
                base = ("paths", api_path, method_name, "responses", "200",
                        "content", "application/json", "schema")
                walk(resp_schema, base, 0, op_id, None)

    return locations


def camel_to_pascal(name):
    if not name:
        return name
    return name[0].upper() + name[1:]


def snake_to_pascal(name):
    return "".join(word.capitalize() for word in name.split("_") if word)


def to_pascal_case(name):
    if "_" in name:
        return snake_to_pascal(name)
    if "-" in name:
        return "".join(word.capitalize() for word in name.split("-") if word)
    return camel_to_pascal(name)


def assign_names(groups):
    """Assign a component name to each fingerprint group."""
    used_names = set()
    names = {}

    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))

    for fp, locs in sorted_groups:
        prop_set = frozenset(locs[0]["prop_names"])
        if prop_set in SEMANTIC_NAMES:
            name = SEMANTIC_NAMES[prop_set]
            if name not in used_names:
                names[fp] = name
                used_names.add(name)

    for fp, locs in sorted_groups:
        if fp in names:
            continue

        field_names = [loc["field_name"] for loc in locs if loc["field_name"]]
        if field_names:
            most_common = Counter(field_names).most_common(1)[0][0]
            candidate = to_pascal_case(most_common)
        else:
            op_ids = sorted(set(loc["op_id"] for loc in locs))
            candidate = camel_to_pascal(op_ids[0])

        name = candidate
        if name in used_names:
            prop_count = len(locs[0]["prop_names"])
            name = f"{candidate}{prop_count}"

        suffix = 2
        while name in used_names:
            name = f"{candidate}{suffix}"
            suffix += 1

        names[fp] = name
        used_names.add(name)

    return names


def resolve_path(obj, path):
    for key in path:
        obj = obj[key]
    return obj


def set_at_path(obj, path, value):
    parent = resolve_path(obj, path[:-1])
    parent[path[-1]] = value


def extract_bottom_up(spec, groups, names):
    """Replace inline schemas with $refs bottom-up (deepest first)."""
    components = {}

    sorted_fps = sorted(
        groups.keys(),
        key=lambda fp: max(loc["depth"] for loc in groups[fp]),
        reverse=True,
    )

    for fp in sorted_fps:
        locs = groups[fp]
        name = names[fp]

        canonical = copy.deepcopy(resolve_path(spec, locs[0]["json_path"]))
        components[name] = canonical

        ref = {"$ref": f"#/components/schemas/{name}"}
        for loc in locs:
            set_at_path(spec, loc["json_path"], ref)

    return components


def collect_wrapper_schemas(spec):
    """Find non-object schemas that generate verbose inline model names.

    Targets two patterns after object schemas have been extracted:
    1. Response array items that are anyOf wrappers or nested arrays
    2. Nested anyOf inside component schema properties
    """
    wrappers = []

    for api_path in sorted(spec.get("paths", {})):
        methods = spec["paths"][api_path]
        for method_name in ("get", "post", "put", "patch", "delete"):
            if method_name not in methods:
                continue
            op = methods[method_name]
            op_id = op.get("operationId", api_path)
            resp_schema = (
                op.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            if not resp_schema:
                continue
            items = resp_schema.get("items")
            if not items or not isinstance(items, dict) or "$ref" in items:
                continue

            base = ["paths", api_path, method_name, "responses", "200",
                    "content", "application/json", "schema", "items"]
            wrappers.append({
                "json_path": base,
                "op_id": op_id,
                "fingerprint": fingerprint(items),
                "context": "items",
                "field_name": None,
            })

            if items.get("type") == "array":
                inner = items.get("items")
                if inner and isinstance(inner, dict) and "$ref" not in inner:
                    inner_path = base + ["items"]
                    wrappers.append({
                        "json_path": inner_path,
                        "op_id": op_id,
                        "fingerprint": fingerprint(inner),
                        "context": "items_inner",
                        "field_name": None,
                    })
                    if "anyOf" in inner:
                        for i, entry in enumerate(inner["anyOf"]):
                            if (isinstance(entry, dict) and "anyOf" in entry
                                    and "$ref" not in entry):
                                wrappers.append({
                                    "json_path": inner_path + ["anyOf", i],
                                    "op_id": op_id,
                                    "fingerprint": fingerprint(entry),
                                    "context": "nested_anyof",
                                    "field_name": None,
                                })

    for schema_name in sorted(
        spec.get("components", {}).get("schemas", {})
    ):
        schema = spec["components"]["schemas"][schema_name]
        for prop_name in sorted(schema.get("properties", {})):
            prop = schema["properties"][prop_name]
            if "anyOf" in prop:
                for i, entry in enumerate(prop["anyOf"]):
                    if (isinstance(entry, dict) and "anyOf" in entry
                            and "$ref" not in entry):
                        wrappers.append({
                            "json_path": ["components", "schemas", schema_name,
                                          "properties", prop_name, "anyOf", i],
                            "op_id": schema_name,
                            "fingerprint": fingerprint(entry),
                            "context": "nested_anyof",
                            "field_name": prop_name,
                        })
            if prop.get("type") == "array":
                items = prop.get("items")
                if not items or not isinstance(items, dict) or "$ref" in items:
                    continue
                if "anyOf" in items or items.get("type") == "array":
                    path = ["components", "schemas", schema_name,
                            "properties", prop_name, "items"]
                    wrappers.append({
                        "json_path": path,
                        "op_id": schema_name,
                        "fingerprint": fingerprint(items),
                        "context": "items",
                        "field_name": prop_name,
                    })
                    if items.get("type") == "array":
                        inner = items.get("items")
                        if (inner and isinstance(inner, dict)
                                and "$ref" not in inner):
                            wrappers.append({
                                "json_path": path + ["items"],
                                "op_id": schema_name,
                                "fingerprint": fingerprint(inner),
                                "context": "items_inner",
                                "field_name": prop_name,
                            })

    return wrappers


def extract_wrapper_schemas(spec):
    """Extract wrapper schemas (anyOf wrappers, nested arrays) as components."""
    wrappers = collect_wrapper_schemas(spec)
    if not wrappers:
        return {}

    groups = defaultdict(list)
    for w in wrappers:
        groups[w["fingerprint"]].append(w)

    existing = set(spec.get("components", {}).get("schemas", {}).keys())
    components = {}

    sorted_fps = sorted(
        groups.keys(),
        key=lambda fp: max(len(w["json_path"]) for w in groups[fp]),
        reverse=True,
    )

    for fp in sorted_fps:
        locs = groups[fp]
        loc = locs[0]

        if loc["context"] == "items":
            if loc.get("field_name"):
                name = to_pascal_case(loc["field_name"]) + "Item"
            else:
                name = camel_to_pascal(loc["op_id"]) + "Item"
        elif loc["context"] == "items_inner":
            if loc.get("field_name"):
                name = to_pascal_case(loc["field_name"]) + "Element"
            else:
                name = camel_to_pascal(loc["op_id"]) + "Element"
        elif loc["context"] == "nested_anyof" and loc.get("field_name"):
            name = to_pascal_case(loc["field_name"]) + "Option"
        else:
            name = camel_to_pascal(loc["op_id"]) + "Value"

        base_name = name
        suffix = 2
        while name in existing or name in components:
            name = f"{base_name}{suffix}"
            suffix += 1

        canonical = copy.deepcopy(resolve_path(spec, locs[0]["json_path"]))
        components[name] = canonical

        ref = {"$ref": f"#/components/schemas/{name}"}
        for loc in locs:
            set_at_path(spec, loc["json_path"], ref)

    return components


def validate(spec, components):
    """Check all $refs resolve and no inline object schemas remain."""
    errors = []

    def check_refs(node, path="root"):
        if isinstance(node, dict):
            if "$ref" in node:
                target = node["$ref"]
                if target.startswith("#/components/schemas/"):
                    schema_name = target.split("/")[-1]
                    if schema_name not in components:
                        errors.append(f"Broken $ref at {path}: {target}")
            else:
                for k, v in node.items():
                    check_refs(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                check_refs(v, f"{path}[{i}]")

    check_refs(spec.get("paths", {}), "paths")
    check_refs(components, "components/schemas")

    remaining = []

    def find_remaining(node, path="paths"):
        if isinstance(node, dict):
            if "$ref" in node:
                return
            if node.get("type") == "object" and "properties" in node:
                remaining.append(path)
                return
            for k, v in node.items():
                find_remaining(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                find_remaining(v, f"{path}[{i}]")

    find_remaining(spec.get("paths", {}))

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    if remaining:
        print(f"  WARNING: {len(remaining)} inline object schemas remain:")
        for r in remaining[:10]:
            print(f"    {r}")

    return len(errors) == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="spec to read")
    parser.add_argument("--output", required=True, help="where to write")
    args = parser.parse_args(argv)

    with open(args.input) as f:
        spec = json.load(f)

    for path in PATHS_TO_REMOVE:
        if path in spec.get("paths", {}):
            del spec["paths"][path]
            print(f"Removed endpoint: {path}")

    locations = walk_and_collect(spec)
    print(f"Found {len(locations)} inline object schemas")

    groups = defaultdict(list)
    for loc in locations:
        groups[loc["fingerprint"]].append(loc)
    unique = len(groups)
    dupes = len(locations) - unique
    print(f"Unique: {unique}, Duplicates: {dupes}")

    names = assign_names(dict(groups))

    components = extract_bottom_up(spec, dict(groups), names)

    spec.setdefault("components", {})["schemas"] = dict(
        sorted(components.items())
    )

    wrapper_components = extract_wrapper_schemas(spec)
    if wrapper_components:
        components.update(wrapper_components)
        spec["components"]["schemas"].update(wrapper_components)
        spec["components"]["schemas"] = dict(
            sorted(spec["components"]["schemas"].items())
        )

    print("\nValidating...")
    ok = validate(spec, spec["components"]["schemas"])
    if ok:
        print("  All $refs valid, no inline schemas remain.")

    with open(args.output, "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")

    obj_count = len(components) - len(wrapper_components)
    print(f"\nExtracted {obj_count} object schemas:")
    for name in sorted(components):
        if name in wrapper_components:
            continue
        fp = next(fp for fp, n in names.items() if n == name)
        count = len(groups[fp])
        props = len(components[name].get("properties", {}))
        print(f"  {name}: {props} props, {count}x")

    if wrapper_components:
        print(f"\nExtracted {len(wrapper_components)} wrapper schemas:")
        for name in sorted(wrapper_components):
            print(f"  {name}")

    print(f"\nTotal: {len(components)} component schemas")
    print(f"Written to {args.output}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
