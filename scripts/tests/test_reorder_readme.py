import os
import re

import pytest

from scripts import reorder_readme

from .conftest import FIXTURES, REPO_ROOT

ORDERING = reorder_readme.read_ordering(os.path.join(REPO_ROOT, "ordering.txt"))
READMES = ["README_python.md", "README_python_async.md", "README_r.md"]


def endpoint_paths(readme):
    return [m.group(1).lstrip("/") for m in re.finditer(r"\*\*[A-Z]+\*\* (/\S+)", readme)]


@pytest.mark.parametrize("name", READMES)
def test_reorders_by_ordering(name):
    with open(os.path.join(FIXTURES, name)) as f:
        readme = f.read()
    new, count = reorder_readme.reorder(readme, ORDERING)
    assert count == 8
    paths = endpoint_paths(new)
    assert sorted(paths) == sorted(endpoint_paths(readme))
    assert paths == sorted(paths, key=ORDERING.index)
    assert paths[0] == "variants"
    assert "llm-query" in paths
    # everything outside the table is untouched
    start = readme.index("## Documentation for API Endpoints")
    assert new[:start] == readme[:start]
    models = re.search(r"^## Documentation for Models", readme, re.M | re.I).start()
    assert new.endswith(readme[models:])


@pytest.mark.parametrize("name", READMES)
def test_idempotent(name):
    with open(os.path.join(FIXTURES, name)) as f:
        readme = f.read()
    once, _ = reorder_readme.reorder(readme, ORDERING)
    twice, _ = reorder_readme.reorder(once, ORDERING)
    assert twice == once


def test_unknown_paths_go_last_alphabetically():
    readme = (
        "## Documentation for API Endpoints\n\n"
        "Class | Method | HTTP request | Description\n"
        "------------ | ------------- | ------------- | -------------\n"
        "*A* | [**z**](x) | **GET** /zzz | \n"
        "*A* | [**y**](x) | **GET** /aaa | \n"
        "*A* | [**g**](x) | **GET** /genes | \n"
        "\n## Documentation For Models\n"
    )
    new, _ = reorder_readme.reorder(readme, ["genes"])
    assert endpoint_paths(new) == ["genes", "aaa", "zzz"]


def test_missing_markers(tmp_path, capsys):
    readme = tmp_path / "README.md"
    readme.write_text("# nothing here\n")
    ordering = tmp_path / "ordering.txt"
    ordering.write_text("genes\n")
    reorder_readme.main(["--readme", str(readme), "--ordering", str(ordering)])
    assert readme.read_text() == "# nothing here\n"
    assert "not found" in capsys.readouterr().out
