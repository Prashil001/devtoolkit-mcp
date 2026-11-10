import pytest

from devtoolkit_mcp.tools.run_tests import (
    _validate_project_path,
    _detect_test_framework,
    _get_python_executable,
    _execute_tests,
    run_tests,
    _terminate_process_tree
)
import subprocess
from unittest.mock import MagicMock, patch


def test_accepts_valid_project_directory(tmp_path):
    result = _validate_project_path(str(tmp_path))

    assert result == tmp_path.resolve()


def test_rejects_empty_project_path():
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_project_path("")


def test_rejects_non_string_project_path():
    with pytest.raises(TypeError, match="must be a string"):
        _validate_project_path(123)


def test_rejects_nonexistent_directory(tmp_path):
    missing_path = tmp_path / "missing"

    with pytest.raises(ValueError, match="does not exist"):
        _validate_project_path(str(missing_path))


def test_rejects_file_instead_of_directory(tmp_path):
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="directory"):
        _validate_project_path(str(file_path))

def test_detects_pytest_from_config(tmp_path):
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\n",
        encoding="utf-8",
    )

    result = _detect_test_framework(tmp_path)

    assert result == {
        "frameworks": ["pytest"],
        "status": "detected",
    }


def test_detects_pytest_from_import(tmp_path):
    (tmp_path / "test_example.py").write_text(
        "import pytest\n",
        encoding="utf-8",
    )

    result = _detect_test_framework(tmp_path)

    assert result == {
        "frameworks": ["pytest"],
        "status": "detected",
    }


def test_detects_unittest_from_import(tmp_path):
    (tmp_path / "test_example.py").write_text(
        "import unittest\n",
        encoding="utf-8",
    )

    result = _detect_test_framework(tmp_path)

    assert result == {
        "frameworks": ["unittest"],
        "status": "detected",
    }


def test_detects_both_frameworks(tmp_path):
    (tmp_path / "test_example.py").write_text(
        "import pytest\nimport unittest\n",
        encoding="utf-8",
    )

    result = _detect_test_framework(tmp_path)

    assert result == {
        "frameworks": ["pytest", "unittest"],
        "status": "multiple_detected",
    }


def test_does_not_assume_every_pyproject_uses_pytest(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\n',
        encoding="utf-8",
    )

    result = _detect_test_framework(tmp_path)

    assert result == {
        "frameworks": [],
        "status": "not_found",
    }


def test_returns_not_found_without_tests(tmp_path):
    result = _detect_test_framework(tmp_path)

    assert result == {
        "frameworks": [],
        "status": "not_found",
    }

def test_uses_project_virtual_environment(tmp_path):
    import sys

    if sys.platform == "win32":
        python_path = tmp_path / ".venv" / "Scripts" / "python.exe"
    else:
        python_path = tmp_path / ".venv" / "bin" / "python"

    python_path.parent.mkdir(parents=True)
    python_path.touch()

    result = _get_python_executable(tmp_path)

    assert result == str(python_path)


def test_falls_back_to_current_python(tmp_path):
    import sys

    result = _get_python_executable(tmp_path)

    assert result == sys.executable

def test_executes_successful_command(tmp_path):
    import sys

    result = _execute_tests(
        tmp_path,
        [sys.executable, "-c", "print('Tests passed')"],
    )

    assert result["status"] == "completed"
    assert result["return_code"] == 0
    assert "Tests passed" in result["output"]


def test_handles_failed_command(tmp_path):
    import sys

    result = _execute_tests(
        tmp_path,
        [sys.executable, "-c", "raise SystemExit(1)"],
    )

    assert result["status"] == "completed"
    assert result["return_code"] == 1


def test_handles_timeout(tmp_path):
    import sys

    result = _execute_tests(
        tmp_path,
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout=1,
    )

    assert result["status"] == "timeout"
    assert result["return_code"] is None


def test_limits_returned_output(tmp_path):
    import sys

    result = _execute_tests(
        tmp_path,
        [sys.executable, "-c", "print('A' * 15000)"],
    )

    assert result["status"] == "completed"
    assert len(result["output"].encode("utf-8")) <= 10000

def test_returns_not_found_without_test_framework(tmp_path):
    result = run_tests(str(tmp_path))

    assert result["status"] == "not_found"
    assert result["framework"] is None


def test_rejects_invalid_timeout(tmp_path):
    result = run_tests(str(tmp_path), timeout=0)

    assert result["status"] == "error"
    assert "Timeout" in result["output"]


def test_rejects_non_integer_timeout(tmp_path):
    result = run_tests(str(tmp_path), timeout="120")

    assert result["status"] == "error"


def test_rejects_timeout_above_limit(tmp_path):
    result = run_tests(str(tmp_path), timeout=601)

    assert result["status"] == "error"

def test_runs_real_pytest_project(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_sample.py").write_text(
        "def test_addition():\n"
        "    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )

    (tmp_path / "pytest.ini").write_text(
        "[pytest]\n",
        encoding="utf-8",
    )

    result = run_tests(str(tmp_path))

    assert result["status"] == "passed"
    assert result["framework"] == "pytest"
    assert result["return_code"] == 0
    assert "1 passed" in result["output"]

def test_runs_real_unittest_project(tmp_path):
    (tmp_path / "test_sample.py").write_text(
        "import unittest\n\n"
        "class SampleTests(unittest.TestCase):\n"
        "    def test_addition(self):\n"
        "        self.assertEqual(2 + 2, 4)\n",
        encoding="utf-8",
    )

    result = run_tests(str(tmp_path))

    assert result["status"] == "passed"
    assert result["framework"] == "unittest"
    assert result["return_code"] == 0
    assert "OK" in result["output"]

def test_reports_failed_pytest_project(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_sample.py").write_text(
        "def test_failure():\n"
        "    assert 2 + 2 == 5\n",
        encoding="utf-8",
    )

    (tmp_path / "pytest.ini").write_text(
        "[pytest]\n",
        encoding="utf-8",
    )

    result = run_tests(str(tmp_path))

    assert result["status"] == "failed"
    assert result["return_code"] == 1
    assert "failed" in result["output"]

def test_reports_timeout(tmp_path, monkeypatch):
    from devtoolkit_mcp.tools import run_tests as run_tests_module


def test_reports_timeout(tmp_path, monkeypatch):
    import importlib

    module = importlib.import_module(
        "devtoolkit_mcp.tools.run_tests"
    )

    (tmp_path / "pytest.ini").write_text(
        "[pytest]\n",
        encoding="utf-8",
    )

    (tmp_path / "test_sample.py").write_text(
        "def test_sample():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    def fake_execute_tests(**kwargs):
        return {
            "status": "timeout",
            "return_code": None,
            "output": "Test execution exceeded the time limit.",
        }

    monkeypatch.setattr(module, "_execute_tests", fake_execute_tests)

    result = module.run_tests(str(tmp_path))

    assert result["status"] == "timeout"
    assert result["return_code"] is None


def test_rejects_nonexistent_project():
    result = run_tests("Z:/definitely-not-a-real-project")

    assert result["status"] == "error"


def test_rejects_boolean_timeout(tmp_path):
    result = run_tests(str(tmp_path), timeout=True)

    assert result["status"] == "error"
    assert "integer" in result["output"]

def test_terminate_process_tree_uses_taskkill_on_windows():
    process = MagicMock()
    process.pid = 1234
    process.poll.return_value = None

    with patch("devtoolkit_mcp.tools.run_tests.os.name", "nt"):
        with patch("devtoolkit_mcp.tools.run_tests.subprocess.run") as mock_run:
            _terminate_process_tree(process)

    mock_run.assert_called_once_with(
        ["taskkill", "/F", "/T", "/PID", "1234"],
        capture_output=True,
        timeout=10,
        shell=False,
        check=False,
    )

def test_execute_tests_creates_new_process_group(tmp_path):
    with patch(
        "devtoolkit_mcp.tools.run_tests.subprocess.Popen"
    ) as mock_popen:
        process = MagicMock()
        process.stdout = MagicMock()
        process.wait.return_value = 0
        process.poll.return_value = 0
        mock_popen.return_value = process

        with patch(
            "devtoolkit_mcp.tools.run_tests.threading.Thread"
        ) as mock_thread:
            reader = MagicMock()
            mock_thread.return_value = reader

            result = _execute_tests(
                project_root=tmp_path,
                command=["python", "-m", "pytest"],
            )

    kwargs = mock_popen.call_args.kwargs

    assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP
    assert kwargs["start_new_session"] is False
    assert result["status"] == "completed"
    reader.start.assert_called_once()
    reader.join.assert_called_once_with()


def test_execute_tests_terminates_process_tree_on_timeout(tmp_path):
    process = MagicMock()
    process.pid = 1234
    process.stdout = MagicMock()
    process.poll.return_value = None
    process.wait.side_effect = [
        subprocess.TimeoutExpired(cmd=["python", "-m", "pytest"], timeout=1),
        -9,
    ]

    with patch(
        "devtoolkit_mcp.tools.run_tests.subprocess.Popen",
        return_value=process,
    ):
        with patch(
            "devtoolkit_mcp.tools.run_tests.subprocess.run"
        ) as mock_taskkill:
            with patch(
                "devtoolkit_mcp.tools.run_tests.threading.Thread"
            ) as mock_thread:
                reader = MagicMock()
                mock_thread.return_value = reader

                result = _execute_tests(
                    project_root=tmp_path,
                    command=["python", "-m", "pytest"],
                    timeout=1,
                )

    mock_taskkill.assert_called_once()
    process.kill.assert_called_once()
    assert result["status"] == "timeout"
    reader.join.assert_any_call(timeout=5)