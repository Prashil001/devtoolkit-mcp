import pytest
import httpx

from devtoolkit_mcp.tools.check_dependencies import (
    _validate_project_path,
    _discover_manifests,
    _parse_requirements_txt,
    _parse_pyproject_toml,
    _get_latest_version,
    _compare_versions,
    _check_vulnerabilities,
    check_dependencies,
)


def test_accepts_valid_project_directory(tmp_path):
    result = _validate_project_path(str(tmp_path))

    assert result == tmp_path.resolve()


def test_rejects_empty_project_path():
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_project_path("")


def test_rejects_non_string_project_path():
    with pytest.raises(ValueError, match="must be a string"):
        _validate_project_path(123)


def test_rejects_nonexistent_directory(tmp_path):
    missing_path = tmp_path / "missing"

    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        _validate_project_path(str(missing_path))


def test_rejects_file_instead_of_directory(tmp_path):
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="directory",
    ):
        _validate_project_path(str(file_path))

def test_discovers_requirements_txt(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("requests==2.31.0", encoding="utf-8")

    result = _discover_manifests(tmp_path)

    assert result == [manifest]


def test_discovers_pyproject_toml(tmp_path):
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text("[project]", encoding="utf-8")

    result = _discover_manifests(tmp_path)

    assert result == [manifest]


def test_discovers_both_manifests(tmp_path):
    requirements = tmp_path / "requirements.txt"
    pyproject = tmp_path / "pyproject.toml"

    requirements.write_text("requests==2.31.0", encoding="utf-8")
    pyproject.write_text("[project]", encoding="utf-8")

    result = _discover_manifests(tmp_path)

    assert result == [requirements, pyproject]


def test_rejects_project_without_manifests(tmp_path):
    with pytest.raises(
        ValueError,
        match="No supported dependency manifest",
    ):
        _discover_manifests(tmp_path)

def test_parses_requirements_txt(tmp_path):
    manifest = tmp_path / "requirements.txt"

    manifest.write_text(
        "requests==2.31.0\n"
        "fastapi>=0.100.0\n"
        "# This is a comment\n"
        "pydantic\n",
        encoding="utf-8",
    )

    result = _parse_requirements_txt(manifest)

    assert result == [
        {"name": "requests", "specifier": "==2.31.0"},
        {"name": "fastapi", "specifier": ">=0.100.0"},
        {"name": "pydantic", "specifier": ""},
    ]


def test_parses_pyproject_toml(tmp_path):
    manifest = tmp_path / "pyproject.toml"

    manifest.write_text(
        """
[project]
dependencies = [
    "requests>=2.31.0",
    "fastapi==0.115.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0"
]
""",
        encoding="utf-8",
    )

    result = _parse_pyproject_toml(manifest)

    assert result == [
        {"name": "requests", "specifier": ">=2.31.0"},
        {"name": "fastapi", "specifier": "==0.115.0"},
        {"name": "pytest", "specifier": ">=8.0"},
    ]


def test_ignores_pip_options_in_requirements(tmp_path):
    manifest = tmp_path / "requirements.txt"

    manifest.write_text(
        "-r base.txt\n"
        "requests==2.31.0\n",
        encoding="utf-8",
    )

    result = _parse_requirements_txt(manifest)

    assert result == [
        {"name": "requests", "specifier": "==2.31.0"}
    ]

def test_get_latest_version_success(monkeypatch):
    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "info": {
                    "version": "2.32.5"
                }
            }

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: MockResponse(),
    )

    result = _get_latest_version("requests")

    assert result == {
        "latest_version": "2.32.5",
        "status": "success",
    }


def test_get_latest_version_package_not_found(monkeypatch):
    class MockResponse:
        status_code = 404

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: MockResponse(),
    )

    result = _get_latest_version("unknown-package")

    assert result["status"] == "package_not_found"


def test_get_latest_version_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr(httpx, "get", mock_get)

    result = _get_latest_version("requests")

    assert result["status"] == "timeout"


def test_get_latest_version_network_error(monkeypatch):
    def mock_get(*args, **kwargs):
        raise httpx.RequestError("Connection failed")

    monkeypatch.setattr(httpx, "get", mock_get)

    result = _get_latest_version("requests")

    assert result["status"] == "network_error"

def test_detects_outdated_package():
    result = _compare_versions(
        "requests",
        "==2.28.0",
        "2.32.5",
    )

    assert result["update_available"] is True
    assert result["status"] == "success"


def test_detects_latest_package():
    result = _compare_versions(
        "requests",
        "==2.32.5",
        "2.32.5",
    )

    assert result["update_available"] is False


def test_detects_newer_declared_version():
    result = _compare_versions(
        "requests",
        "==2.33.0",
        "2.32.5",
    )

    assert result["update_available"] is False


def test_handles_unpinned_package():
    result = _compare_versions(
        "requests",
        ">=2.28.0",
        "2.32.5",
    )

    assert result["status"] == "unpinned_version"
    assert result["update_available"] is None


def test_handles_missing_latest_version():
    result = _compare_versions(
        "requests",
        "==2.28.0",
        None,
    )

    assert result["status"] == "version_unavailable"


def test_handles_invalid_version():
    result = _compare_versions(
        "requests",
        "==invalid",
        "2.32.5",
    )

    assert result["status"] == "invalid_version"

def test_finds_vulnerabilities(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "vulns": [
                    {
                        "id": "GHSA-example",
                        "summary": "Example vulnerability",
                        "aliases": ["CVE-2025-12345"],
                    }
                ]
            }

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: MockResponse(),
    )

    result = _check_vulnerabilities("requests", "2.28.0")

    assert result["status"] == "success"
    assert len(result["vulnerabilities"]) == 1
    assert result["vulnerabilities"][0]["id"] == "GHSA-example"


def test_no_vulnerabilities_found(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"vulns": []}

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: MockResponse(),
    )

    result = _check_vulnerabilities("requests", "2.32.5")

    assert result["status"] == "success"
    assert result["vulnerabilities"] == []


def test_handles_missing_version():
    result = _check_vulnerabilities("requests", None)

    assert result["status"] == "version_unavailable"


def test_handles_osv_timeout(monkeypatch):
    def mock_post(*args, **kwargs):
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr(httpx, "post", mock_post)

    result = _check_vulnerabilities("requests", "2.28.0")

    assert result["status"] == "timeout"


def test_handles_osv_network_error(monkeypatch):
    def mock_post(*args, **kwargs):
        raise httpx.RequestError("Connection failed")

    monkeypatch.setattr(httpx, "post", mock_post)

    result = _check_vulnerabilities("requests", "2.28.0")

    assert result["status"] == "network_error"

def test_check_dependencies_integration(tmp_path, monkeypatch):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text(
        "requests==2.28.0\n",
        encoding="utf-8",
    )

    def mock_pypi(package_name):
        return {
            "latest_version": "2.32.5",
            "status": "success",
        }

    def mock_osv(package_name, version):
        return {
            "vulnerabilities": [],
            "status": "success",
        }

    monkeypatch.setattr(
        "devtoolkit_mcp.tools.check_dependencies._get_latest_version",
        mock_pypi,
    )

    monkeypatch.setattr(
        "devtoolkit_mcp.tools.check_dependencies._check_vulnerabilities",
        mock_osv,
    )

    result = check_dependencies(str(tmp_path))

    assert result["total_dependencies"] == 1

    dependency = result["dependencies"][0]

    assert dependency["name"] == "requests"
    assert dependency["declared_version"] == "2.28.0"
    assert dependency["latest_version"] == "2.32.5"
    assert dependency["update_available"] is True
    assert dependency["vulnerability_status"] == "success"


def test_check_dependencies_rejects_oversized_manifest(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("x" * 1_000_001, encoding="utf-8")

    with pytest.raises(ValueError, match="size limit"):
        check_dependencies(str(tmp_path))