import json

import pytest

from scripts import compute_version as cv


@pytest.mark.parametrize("tag,expected", [
    ("v1.2", "1.2.0"),
    ("v1.0.2", "1.0.2"),
    ("1.3", "1.3.0"),
    ("v10.20.30", "10.20.30"),
])
def test_release_tag_normalization(tag, expected):
    assert cv.release_versions(tag) == (expected, expected)


@pytest.mark.parametrize("tag", ["v.1.0.0.1", "1.2-beta", "v1", "main_v1.0.0", "", "v1.2.3.4"])
def test_release_tag_rejected(tag):
    with pytest.raises(cv.VersionError):
        cv.release_versions(tag)


def test_dev_versions():
    assert cv.dev_versions((1, 2, 0), "20261012153000") == (
        "1.2.1.dev20261012153000",
        "1.2.0.9000",
    )


def test_dev_versions_rejects_bad_timestamp():
    with pytest.raises(cv.VersionError):
        cv.dev_versions((1, 2, 0), "2026-10-12")


def test_latest_release_skips_drafts_prereleases_and_malformed():
    releases = [
        {"tag_name": "v.1.0.0.1"},
        {"tag_name": "v2.0", "prerelease": True},
        {"tag_name": "v1.9", "draft": True},
        {"tag_name": "v1.2"},
        {"tag_name": "v1.3"},
        {"tag_name": "v1.0.2"},
    ]
    assert cv.latest_release(releases) == (1, 3, 0)


def test_latest_release_none():
    assert cv.latest_release([]) == (0, 0, 0)
    assert cv.latest_release([{"tag_name": "nope"}]) == (0, 0, 0)


def test_main_release(capsys):
    assert cv.main(["--channel", "release", "--tag", "v1.3"]) == 0
    assert capsys.readouterr().out == "version=1.3.0\nr_version=1.3.0\n"


def test_main_release_bad_tag(capsys):
    assert cv.main(["--channel", "release", "--tag", "v.1.0.0.1"]) == 1
    assert capsys.readouterr().out == ""


def test_main_dev_latest_tag(capsys):
    assert cv.main(["--channel", "dev", "--latest-tag", "v1.2", "--timestamp", "20261012153000"]) == 0
    assert capsys.readouterr().out == "version=1.2.1.dev20261012153000\nr_version=1.2.0.9000\n"


def test_main_dev_no_release(capsys):
    assert cv.main(["--channel", "dev", "--timestamp", "20261012153000"]) == 0
    assert capsys.readouterr().out == "version=0.0.1.dev20261012153000\nr_version=0.0.0.9000\n"


def test_main_dev_releases_json(tmp_path, capsys):
    path = tmp_path / "releases.json"
    path.write_text(json.dumps([{"tag_name": "v.1.0.0.1"}, {"tag_name": "v1.0.2"}]))
    assert cv.main(["--channel", "dev", "--releases-json", str(path), "--timestamp", "20261012153000"]) == 0
    assert capsys.readouterr().out == "version=1.0.3.dev20261012153000\nr_version=1.0.2.9000\n"
