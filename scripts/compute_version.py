"""Compute client package versions from igvf-catalog releases.

Prints `version=...` and `r_version=...` lines suitable for $GITHUB_OUTPUT.

Release channel: the igvf-catalog release tag, normalized to X.Y.Z
    --channel release --tag v1.3          -> version=1.3.0       r_version=1.3.0

Dev channel: one patch past the latest igvf-catalog release
    --channel dev --latest-tag v1.2 --timestamp 20261012153000
                                          -> version=1.2.1.dev20261012153000
                                             r_version=1.2.0.9000
    The base release can instead come from --releases-json, a file holding the
    GitHub "list releases" API response. Drafts, prereleases and tags that
    don't parse are skipped and the highest remaining version is used. With
    no usable release the base is 0.0.0.
"""

import argparse
import json
import re
import sys

TAG_RE = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")


class VersionError(ValueError):
    pass


def parse_tag(tag):
    """Return (major, minor, patch) for tags like v1.3 or 1.0.2."""
    match = TAG_RE.match(tag.strip()) if tag else None
    if not match:
        raise VersionError(f"tag {tag!r} does not match {TAG_RE.pattern}")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch or 0)


def format_version(parts):
    return ".".join(str(p) for p in parts)


def latest_release(releases):
    """Highest parseable version among published, non-prerelease releases."""
    best = None
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        try:
            parts = parse_tag(release.get("tag_name", ""))
        except VersionError:
            continue
        if best is None or parts > best:
            best = parts
    return best or (0, 0, 0)


def release_versions(tag):
    version = format_version(parse_tag(tag))
    return version, version


def dev_versions(base, timestamp):
    if not re.fullmatch(r"\d{14}", timestamp):
        raise VersionError(f"timestamp {timestamp!r} is not YYYYMMDDHHMMSS")
    major, minor, patch = base
    version = f"{major}.{minor}.{patch + 1}.dev{timestamp}"
    r_version = f"{major}.{minor}.{patch}.9000"
    return version, r_version


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--channel", choices=["dev", "release"], required=True)
    parser.add_argument("--tag", help="release tag (release channel)")
    parser.add_argument("--latest-tag", help="latest igvf-catalog release tag (dev channel)")
    parser.add_argument("--releases-json", help="GitHub releases API response (dev channel)")
    parser.add_argument("--timestamp", help="YYYYMMDDHHMMSS (dev channel)")
    args = parser.parse_args(argv)

    try:
        if args.channel == "release":
            if not args.tag:
                parser.error("--tag is required for the release channel")
            version, r_version = release_versions(args.tag)
        else:
            if not args.timestamp:
                parser.error("--timestamp is required for the dev channel")
            if args.releases_json:
                with open(args.releases_json) as f:
                    base = latest_release(json.load(f))
            elif args.latest_tag:
                base = latest_release([{"tag_name": args.latest_tag}])
            else:
                base = (0, 0, 0)
            version, r_version = dev_versions(base, args.timestamp)
    except VersionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"version={version}")
    print(f"r_version={r_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
