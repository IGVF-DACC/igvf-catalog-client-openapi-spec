import importlib
import json
import sys

import pytest

from scripts import smoke_test_python as st

PACKAGE = "fake_catalog_client"


def make_spec(version, operations=st.MIN_OPERATIONS):
    paths = {f"/thing{i}": {"get": {"operationId": f"thing{i}"}, "parameters": []} for i in range(operations)}
    return {"openapi": "3.0.3", "info": {"version": version}, "paths": paths}


@pytest.fixture
def fake_package(tmp_path, monkeypatch):
    """Return a function that writes a fake package (with an optional spec) and imports it."""
    monkeypatch.syspath_prepend(str(tmp_path))

    def make(spec=None, raw=None):
        pkg = tmp_path / PACKAGE
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "0"\n')
        if spec is not None:
            raw = json.dumps(spec)
        if raw is not None:
            (pkg / st.SPEC_FILE).write_text(raw)
        importlib.invalidate_caches()
        return PACKAGE

    yield make
    sys.modules.pop(PACKAGE, None)


@pytest.mark.parametrize("version,expected", [
    ("1.3.0", "1.3.0"),
    ("1.3.0.post1", "1.3.0"),
    ("1.3.0.post12", "1.3.0"),
    ("1.3.1.dev20261116230925", "1.3.1.dev20261116230925"),
])
def test_spec_version(version, expected):
    assert st.spec_version(version) == expected


@pytest.mark.parametrize("version,spec_version", [
    ("1.3.0", "1.3.0"),
    ("1.3.0.post1", "1.3.0"),
    ("1.3.1.dev20261116230925", "1.3.1.dev20261116230925"),
])
def test_check_spec_passes(fake_package, version, spec_version):
    st.check_spec(fake_package(make_spec(spec_version)), version)


def test_check_spec_missing_file(fake_package):
    with pytest.raises(AssertionError, match="doesn't ship"):
        st.check_spec(fake_package(), "1.3.0")


def test_check_spec_invalid_json(fake_package):
    with pytest.raises(json.JSONDecodeError):
        st.check_spec(fake_package(raw="{not json"), "1.3.0")


def test_check_spec_too_few_operations(fake_package):
    with pytest.raises(AssertionError, match="operations"):
        st.check_spec(fake_package(make_spec("1.3.0", operations=st.MIN_OPERATIONS - 1)), "1.3.0")


@pytest.mark.parametrize("version,spec_version", [
    ("1.3.0.post1", "1.3.0.post1"),  # the spec states the API version, not the package's
    ("1.3.0.post1", "1.2.0"),
    ("1.3.1.dev20261116230925", "1.3.1"),
])
def test_check_spec_version_mismatch(fake_package, version, spec_version):
    with pytest.raises(AssertionError, match="info.version"):
        st.check_spec(fake_package(make_spec(spec_version)), version)
