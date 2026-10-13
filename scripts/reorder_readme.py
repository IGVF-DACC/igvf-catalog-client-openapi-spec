"""Reorder the API Endpoints table in a generated README to match ordering.txt.

Works for the python, python asyncio and R generator READMEs. The table sits
between "## Documentation for API Endpoints" and "## Documentation For Models"
(python) or "## Documentation for Models" (R).
"""

import argparse
import re

START_MARKER = re.compile(r"^## Documentation for API Endpoints[ \t]*$", re.M)
END_MARKER = re.compile(r"^## Documentation for Models[ \t]*$", re.M | re.I)
PATH_IN_ROW = re.compile(
    r"\*\*(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\*\*\s+(/\S+)"
)


def read_ordering(ordering_path):
    with open(ordering_path) as f:
        return [line.strip() for line in f if line.strip()]


# Extract path from each row: look for **<VERB>** /path pattern
def extract_path(row):
    match = PATH_IN_ROW.search(row)
    if match:
        # Strip leading / and any trailing whitespace/pipe
        return match.group(1).lstrip("/").rstrip()
    return None


def reorder(readme, ordered_paths):
    """Return (new_readme, row_count), or (None, 0) if the markers are missing."""
    priority = {path: i for i, path in enumerate(ordered_paths)}

    start = START_MARKER.search(readme)
    end = END_MARKER.search(readme, start.end()) if start else None
    if not start or not end:
        return None, 0

    before = readme[:start.start()]
    section = readme[start.start():end.start()]
    after = readme[end.start():]

    # Separate header lines (title, blank, column headers, separator) from data rows
    header_lines = []
    data_rows = []
    in_data = False

    for line in section.split("\n"):
        if not in_data:
            header_lines.append(line)
            # After the separator line (---), data rows begin
            if re.match(r"^-+\s*\|", line):
                in_data = True
        else:
            if line.strip():
                data_rows.append(line)
            # preserve trailing blank lines as part of the section end

    # Sort rows by priority
    def sort_key(row):
        path = extract_path(row)
        if path and path in priority:
            return (0, priority[path])
        # Not in ordering.txt: put at end, sorted alphabetically by path
        return (1, path or "")

    data_rows.sort(key=sort_key)

    new_section = "\n".join(header_lines) + "\n" + "\n".join(data_rows) + "\n\n"
    return before + new_section + after, len(data_rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", required=True)
    parser.add_argument("--ordering", required=True)
    args = parser.parse_args(argv)

    with open(args.readme) as f:
        readme = f.read()

    new_readme, count = reorder(readme, read_ordering(args.ordering))
    if new_readme is None:
        print(f"API Endpoints section not found in {args.readme}; leaving it unchanged")
        return

    with open(args.readme, "w") as f:
        f.write(new_readme)

    print(f"Reordered {count} endpoint rows in {args.readme}")


if __name__ == "__main__":
    main()
