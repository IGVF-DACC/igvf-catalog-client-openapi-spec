"""Clean up openapi_spec.json before code generation.

- Remove unwanted endpoints (health, autocomplete)
- Fix spec errors (e.g. missing array items schema on /llm-query)
"""

import argparse
import json

PATHS_TO_REMOVE = ["/health", "/autocomplete"]


def clean_spec(spec):
    # Remove unwanted paths
    for path in PATHS_TO_REMOVE:
        if path in spec.get("paths", {}):
            del spec["paths"][path]
            print(f"Removed {path}")
        else:
            print(f"Not found (skipping): {path}")

    # Fix /llm-query: aql_result array is missing "items"
    llm_query = spec.get("paths", {}).get("/llm-query", {})
    aql_result = (
        llm_query
        .get("post", {})
        .get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("properties", {})
        .get("aql_result", {})
    )
    if aql_result.get("type") == "array" and "items" not in aql_result:
        aql_result["items"] = {}
        print("Fixed /llm-query: added missing items schema to aql_result array")

    return spec


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="spec to read")
    parser.add_argument(
        "--output", help="where to write the result (default: --input)"
    )
    args = parser.parse_args(argv)

    with open(args.input) as f:
        spec = json.load(f)

    clean_spec(spec)

    with open(args.output or args.input, "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")

    print("Done.")


if __name__ == "__main__":
    main()
