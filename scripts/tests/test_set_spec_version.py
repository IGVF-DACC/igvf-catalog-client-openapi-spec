import json

import pytest

from scripts import set_spec_version


def test_set_version(fixture_spec):
    spec = set_spec_version.set_version(fixture_spec, "1.3.1.dev1", "catalog-api-dev.demo.igvf.org")
    assert spec["info"]["version"] == "1.3.1.dev1"


def test_wrong_host(fixture_spec):
    with pytest.raises(set_spec_version.SpecError):
        set_spec_version.set_version(fixture_spec, "1.3.0", "api.catalogkg.igvf.org")


def test_no_host_check(fixture_spec):
    assert set_spec_version.set_version(fixture_spec, "9.9.9")["info"]["version"] == "9.9.9"


def test_main_multiple_files(spec_file, tmp_path):
    other = tmp_path / "other.json"
    other.write_text(spec_file.read_text())
    rc = set_spec_version.main([str(spec_file), str(other), "--version", "2.0.0",
                                "--expect-host", "catalog-api-dev.demo.igvf.org"])
    assert rc == 0
    for p in (spec_file, other):
        assert json.loads(p.read_text())["info"]["version"] == "2.0.0"


def test_main_wrong_host_leaves_file(spec_file):
    before = spec_file.read_text()
    assert set_spec_version.main([str(spec_file), "--version", "2.0.0", "--expect-host", "example.org"]) == 1
    assert spec_file.read_text() == before
