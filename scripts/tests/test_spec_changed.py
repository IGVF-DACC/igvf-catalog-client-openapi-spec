import json

from scripts import spec_changed


def write(path, spec):
    path.write_text(json.dumps(spec))
    return str(path)


def test_ignores_info_version(tmp_path, fixture_spec, capsys):
    old = write(tmp_path / "old.json", {**fixture_spec, "info": {**fixture_spec["info"], "version": "1.0.0"}})
    new = write(tmp_path / "new.json", {**fixture_spec, "info": {**fixture_spec["info"], "version": "2.0.0"}})
    spec_changed.main([old, new])
    assert capsys.readouterr().out == "false\n"


def test_detects_change(tmp_path, fixture_spec, capsys):
    old = write(tmp_path / "old.json", fixture_spec)
    changed = json.loads(json.dumps(fixture_spec))
    del changed["paths"]["/genes"]
    new = write(tmp_path / "new.json", changed)
    spec_changed.main([old, new])
    assert capsys.readouterr().out == "true\n"


def test_missing_or_empty_old_counts_as_changed(tmp_path, fixture_spec, capsys):
    new = write(tmp_path / "new.json", fixture_spec)
    spec_changed.main([str(tmp_path / "missing.json"), new])
    empty = tmp_path / "empty.json"
    empty.write_text("")
    spec_changed.main([str(empty), new])
    assert capsys.readouterr().out == "true\ntrue\n"
