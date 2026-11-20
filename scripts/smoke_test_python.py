"""Offline smoke test for a generated Python client installed in this interpreter.

Imports the package, checks __version__, builds the API class and checks a few
generated methods exist. Also checks the package ships openapi_spec_processed.json
and that its info.version is __version__ without any .postN suffix (a post-release
repackages the same API; a dev build's spec carries the full dev version). Run it
against the installed wheel, not the source tree. Makes no network calls.
"""

import argparse
import asyncio
import importlib
import json
import re
import sys
from importlib import resources

EXPECTED_METHODS = ["genes", "variants", "genes_from_variants", "llm_query"]
SPEC_FILE = "openapi_spec_processed.json"
MIN_OPERATIONS = 50
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def spec_version(version):
    """The info.version a package of this version ships: 1.3.0.post1 -> 1.3.0."""
    return re.sub(r"\.post\d+$", "", version)


def check(module, api_name, version, methods):
    assert module.__version__ == version, f"__version__ is {module.__version__!r}, expected {version!r}"
    api = getattr(module, api_name)(module.ApiClient())
    missing = [m for m in methods if not callable(getattr(api, m, None))]
    assert not missing, f"{api_name} is missing methods: {missing}"


def check_spec(package, version):
    path = resources.files(package).joinpath(SPEC_FILE)
    assert path.is_file(), f"{package} doesn't ship {SPEC_FILE}"
    spec = json.loads(path.read_text())
    operations = sum(
        1 for item in (spec.get("paths") or {}).values() for method in item if method in HTTP_METHODS
    )
    assert operations >= MIN_OPERATIONS, f"{SPEC_FILE} has {operations} operations, expected at least {MIN_OPERATIONS}"
    expected = spec_version(version)
    actual = (spec.get("info") or {}).get("version")
    assert actual == expected, f"{SPEC_FILE} info.version is {actual!r}, expected {expected!r}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, help="import name")
    parser.add_argument("--api", required=True, help="API class name")
    parser.add_argument("--version", required=True)
    parser.add_argument("--asyncio", action="store_true", help="construct the client inside a running event loop")
    args = parser.parse_args(argv)

    module = importlib.import_module(args.package)
    if args.asyncio:
        async def run():
            check(module, args.api, args.version, EXPECTED_METHODS)
        asyncio.run(run())
    else:
        check(module, args.api, args.version, EXPECTED_METHODS)
    check_spec(args.package, args.version)
    print(f"{args.package} {args.version}: {args.api} and {SPEC_FILE} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
