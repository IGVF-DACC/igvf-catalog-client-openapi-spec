import pytest

from scripts import bump_mcp

PYPROJECT = '''[project]
name = "igvf-catalog-mcp"
dynamic = ["version"]
dependencies = [
    "mcp>=1.0.0",
    "igvf-catalog-async-client @ git+https://github.com/IGVF-DACC/igvf-catalog-async-python-client@dev",
]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
'''


def test_bump_init():
    text = '"""IGVF Catalog MCP."""\n\n__version__ = "0.1.0"\n'
    assert bump_mcp.bump_init(text, "1.4.0") == '"""IGVF Catalog MCP."""\n\n__version__ = "1.4.0"\n'


def test_bump_init_requires_one_version_line():
    with pytest.raises(bump_mcp.BumpError):
        bump_mcp.bump_init("x = 1\n", "1.4.0")


@pytest.mark.parametrize("dependency", [
    "igvf-catalog-async-client @ git+https://github.com/IGVF-DACC/igvf-catalog-async-python-client@dev",
    "igvf-catalog-async-client==1.3.0",
    "igvf-catalog-async-client>=1.3",
    "igvf-catalog-async-client",
])
def test_bump_pyproject(dependency):
    text = PYPROJECT.replace(
        "igvf-catalog-async-client @ git+https://github.com/IGVF-DACC/igvf-catalog-async-python-client@dev", dependency
    )
    new = bump_mcp.bump_pyproject(text, "1.4.0")
    assert '"igvf-catalog-async-client==1.4.0",' in new
    assert '"mcp>=1.0.0",' in new
    assert new.count("igvf-catalog-async-client") == 1


def test_bump_pyproject_ignores_similar_names():
    text = PYPROJECT.replace('    "mcp>=1.0.0",\n', '    "igvf-catalog-async-client-extras>=1",\n')
    new = bump_mcp.bump_pyproject(text, "1.4.0")
    assert '"igvf-catalog-async-client-extras>=1"' in new


def test_bump_pyproject_requires_the_dependency():
    with pytest.raises(bump_mcp.BumpError):
        bump_mcp.bump_pyproject('dependencies = ["mcp"]\n', "1.4.0")


def test_main(tmp_path):
    (tmp_path / "src" / "igvf_catalog_mcp").mkdir(parents=True)
    (tmp_path / "src" / "igvf_catalog_mcp" / "__init__.py").write_text('__version__ = "0.1.0"\n')
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    assert bump_mcp.main(["--repo-dir", str(tmp_path), "--version", "1.4.0"]) == 0
    assert (tmp_path / "src" / "igvf_catalog_mcp" / "__init__.py").read_text() == '__version__ = "1.4.0"\n'
    assert '"igvf-catalog-async-client==1.4.0"' in (tmp_path / "pyproject.toml").read_text()
