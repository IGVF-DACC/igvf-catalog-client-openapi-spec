import json
import os

import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture
def fixture_spec():
    with open(os.path.join(FIXTURES, "spec.json")) as f:
        return json.load(f)


@pytest.fixture
def spec_file(tmp_path, fixture_spec):
    path = tmp_path / "openapi_spec.json"
    path.write_text(json.dumps(fixture_spec))
    return path
