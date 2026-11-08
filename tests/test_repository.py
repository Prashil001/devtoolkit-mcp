import pytest

from devtoolkit_mcp.tools.repository import analyze_repository


def test_analyze_repository_returns_project_information(tmp_path):
    # Arrange: Create a sample repository
    project = tmp_path / "sample-project"
    project.mkdir()

    (project / "main.py").write_text("print('Hello')", encoding="utf-8")
    (project / "app.js").write_text("console.log('Hello')", encoding="utf-8")
    (project / "pyproject.toml").write_text("[project]", encoding="utf-8")

    # Act: Analyze the repository
    result = analyze_repository(str(project))

    # Assert: Verify the result
    assert result["project_name"] == "sample-project"
    assert result["files_scanned"] == 3
    assert result["languages"]["Python"] == 1
    assert result["languages"]["JavaScript"] == 1
    assert "pyproject.toml" in result["important_files"]


def test_analyze_repository_ignores_virtual_environment(tmp_path):
    project = tmp_path / "sample-project"
    project.mkdir()

    venv = project / ".venv"
    venv.mkdir()

    (venv / "hidden.py").write_text("print('hidden')", encoding="utf-8")
    (project / "main.py").write_text("print('visible')", encoding="utf-8")

    result = analyze_repository(str(project))

    assert result["files_scanned"] == 1
    assert result["languages"]["Python"] == 1


def test_analyze_repository_rejects_nonexistent_path(tmp_path):
    invalid_path = tmp_path / "does-not-exist"

    with pytest.raises(ValueError, match="does not exist"):
        analyze_repository(str(invalid_path))


def test_analyze_repository_rejects_file_path(tmp_path):
    file_path = tmp_path / "example.py"
    file_path.write_text("print('hello')", encoding="utf-8")

    with pytest.raises(ValueError, match="not a directory"):
        analyze_repository(str(file_path))


@pytest.mark.parametrize("max_files", [0, -1, 20001])
def test_analyze_repository_rejects_invalid_file_limit(tmp_path, max_files):
    with pytest.raises(ValueError, match="max_files"):
        analyze_repository(str(tmp_path), max_files=max_files)


def test_analyze_repository_respects_file_limit(tmp_path):
    project = tmp_path / "sample-project"
    project.mkdir()

    for number in range(5):
        (project / f"file_{number}.py").write_text(
            "print('hello')",
            encoding="utf-8",
        )

    result = analyze_repository(str(project), max_files=2)

    assert result["files_scanned"] == 2
    assert result["truncated"] is True