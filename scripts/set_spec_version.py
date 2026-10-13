"""Set info.version in one or more spec files, in place.

With --expect-host, also check that servers[0].url points at that host, so a
dev spec can't be released (or the reverse) by accident.
"""

import argparse
import json
import sys
from urllib.parse import urlparse


class SpecError(ValueError):
    pass


def set_version(spec, version, expect_host=None):
    if expect_host:
        servers = spec.get("servers") or [{}]
        url = servers[0].get("url", "")
        host = urlparse(url).hostname
        if host != expect_host:
            raise SpecError(
                f"servers[0].url is {url!r}, expected host {expect_host!r}"
            )
    spec.setdefault("info", {})["version"] = version
    return spec


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="spec files to update")
    parser.add_argument("--version", required=True)
    parser.add_argument("--expect-host")
    args = parser.parse_args(argv)

    for path in args.files:
        with open(path) as f:
            spec = json.load(f)
        try:
            set_version(spec, args.version, args.expect_host)
        except SpecError as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            return 1
        with open(path, "w") as f:
            json.dump(spec, f, indent=2)
            f.write("\n")
        print(f"Set info.version={args.version} in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
