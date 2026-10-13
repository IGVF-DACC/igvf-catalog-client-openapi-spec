"""Print `true` if two specs differ (ignoring info.version), else `false`.

A missing or empty OLD file counts as changed, so the first run always
generates clients.
"""

import argparse
import copy
import json
import os


def normalize(spec):
    spec = copy.deepcopy(spec)
    spec.get("info", {}).pop("version", None)
    return spec


def specs_differ(old, new):
    return normalize(old) != normalize(new)


def load(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", help="previously committed spec (may be missing)")
    parser.add_argument("new", help="freshly generated spec")
    args = parser.parse_args(argv)

    old = load(args.old)
    new = load(args.new)
    if new is None:
        parser.error(f"{args.new} is missing or empty")

    changed = old is None or specs_differ(old, new)
    print("true" if changed else "false")


if __name__ == "__main__":
    main()
