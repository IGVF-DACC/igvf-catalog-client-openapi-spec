"""Set the igvf-catalog-mcp version and pin it to the matching async client.

Rewrites `__version__ = "..."` in src/igvf_catalog_mcp/__init__.py and the
single `igvf-catalog-async-client...` dependency in pyproject.toml to
`igvf-catalog-async-client==<version>`.
"""

import argparse
import os
import re
import sys

INIT_PATH = os.path.join("src", "igvf_catalog_mcp", "__init__.py")
VERSION_RE = re.compile(r'^__version__\s*=\s*["\'][^"\']*["\']', re.M)
DEPENDENCY_RE = re.compile(r'"igvf-catalog-async-client(?:[\s@=<>!~\[;][^"]*)?"')


class BumpError(ValueError):
    pass


def bump_init(text, version):
    new, count = VERSION_RE.subn(f'__version__ = "{version}"', text)
    if count != 1:
        raise BumpError(f"expected one __version__ line in {INIT_PATH}, found {count}")
    return new


def bump_pyproject(text, version):
    new, count = DEPENDENCY_RE.subn(f'"igvf-catalog-async-client=={version}"', text)
    if count != 1:
        raise BumpError(f"expected one igvf-catalog-async-client dependency in pyproject.toml, found {count}")
    return new


def rewrite(path, func, version):
    with open(path) as f:
        text = f.read()
    with open(path, "w") as f:
        f.write(func(text, version))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-dir", required=True, help="igvf-catalog-mcp checkout")
    parser.add_argument("--version", required=True)
    args = parser.parse_args(argv)

    try:
        rewrite(os.path.join(args.repo_dir, INIT_PATH), bump_init, args.version)
        rewrite(os.path.join(args.repo_dir, "pyproject.toml"), bump_pyproject, args.version)
    except BumpError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"igvf-catalog-mcp {args.version}, pinned to igvf-catalog-async-client=={args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
