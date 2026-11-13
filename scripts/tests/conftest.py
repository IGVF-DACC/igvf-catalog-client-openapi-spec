import json
import os

import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# spec.json: the format trpc-openapi 1.x produced (igvf-catalog before PR #956).
# spec_trpc_to_openapi.json: the format trpc-to-openapi 3.x produces. It is an
# unmodified dump of igvf-catalog@15f86847, cut down to seven paths.
OLD_SPEC = "spec.json"
NEW_SPEC = "spec_trpc_to_openapi.json"


def load_spec(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


def write_spec(tmp_path, spec):
    path = tmp_path / "openapi_spec.json"
    path.write_text(json.dumps(spec))
    return path


@pytest.fixture(params=[OLD_SPEC, NEW_SPEC])
def fixture_spec(request):
    return load_spec(request.param)


@pytest.fixture
def spec_file(tmp_path, fixture_spec):
    return write_spec(tmp_path, fixture_spec)


@pytest.fixture
def new_spec():
    return load_spec(NEW_SPEC)


@pytest.fixture
def new_spec_file(tmp_path, new_spec):
    return write_spec(tmp_path, new_spec)
