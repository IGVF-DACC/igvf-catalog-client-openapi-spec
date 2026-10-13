"""Offline smoke test for a generated Python client installed in this interpreter.

Imports the package, checks __version__, builds the API class and checks a few
generated methods exist. Makes no network calls.
"""

import argparse
import asyncio
import importlib
import sys

EXPECTED_METHODS = ["genes", "variants", "genes_from_variants", "llm_query"]


def check(module, api_name, version, methods):
    assert module.__version__ == version, f"__version__ is {module.__version__!r}, expected {version!r}"
    api = getattr(module, api_name)(module.ApiClient())
    missing = [m for m in methods if not callable(getattr(api, m, None))]
    assert not missing, f"{api_name} is missing methods: {missing}"


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
    print(f"{args.package} {args.version}: {args.api} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
