import os
import signal
import ast
import subprocess
import sys
import threading
import tomllib
from pathlib import Path


def _validate_project_path(project_path: str) -> Path:
    """Validate the supplied project directory."""

    if not isinstance(project_path, str):
        raise TypeError("Project path must be a string.")

    if not project_path.strip():
        raise ValueError("Project path cannot be empty.")

    root = Path(project_path).expanduser()

    if not root.exists():
        raise ValueError("Project directory does not exist.")

    if root.is_symlink():
        raise ValueError("Symbolic links are not supported.")

    if not root.is_dir():
        raise ValueError("Path must point to a directory.")

    return root.resolve()


def _has_pytest_config(project_root: Path) -> bool:
    """check whether the project has explicit pytest configuration"""

    if (project_root/"pytest.ini").is_file():
        return True
    
    pyproject_file = project_root/"pyproject.toml"

    if pyproject_file.is_file():
        try:
            with pyproject_file.open("rb") as file:
                config = tomllib.load(file)
            
            if "pytest" in config.get("tool", {}):
                return True
            
        except (tomllib.TOMLDecodeError, OSError):
            pass

    config_files = {
        "setup.cfg": "[tool:pytest]",
        "tox.ini":"[pytest]",
    }

    for filename, section in config_files.items():
        config_file = project_root/filename

        if config_file.is_file():
            try:
                content = config_file.read_text(encoding="utf-8").lower()
                if section.lower() in content:
                    return True
                
            except (OSError, UnicodeDecodeError):
                continue
    return False


def _get_test_framework_imports(project_root: Path) -> set[str]:
    """Find pytest and unittest imports in test files"""

    test_files = set(project_root.glob("test_*.py"))
    test_files.update(project_root.glob("*_test.py"))

    tests_directory = project_root/ "tests"

    if tests_directory.is_dir() and not tests_directory.is_symlink():
        test_files.update(tests_directory.rglob("*.py"))
    
    detected = set()

    for test_file in test_files:
        if test_file.is_symlink():
            continue

        try:
            source = test_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "pytest":
                        detected.add("pytest")
                    if alias.name == "unittest":
                        detected.add("unittest")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "pytest" or (
                    node.module and node.module.startswith("pytest.")
                ):
                    detected.add("pytest")
                if node.module == "unittest" or (
                    node.module and node.module.startswith("unittest.")
                ):
                    detected.add("unittest")
    return detected

def _detect_test_framework(project_root: Path) -> dict:
    """Detect pytest and unittest using configuration and imports"""

    detected = _get_test_framework_imports(project_root)

    if _has_pytest_config(project_root):
        detected.add("pytest")
    
    frameworks = sorted(detected)

    if len(frameworks) > 1:
        status = "multiple_detected"
    elif len(frameworks) == 1:
        status = "detected"
    else:
        status = "not_found"

    return {
        "frameworks": frameworks,
        "status": status,
    }


def _get_python_executable(project_root: Path) -> str:
    """Find the Python executable for the target project"""

    if sys.platform == "win32":
        python_path = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        python_path = project_root / ".venv" / "bin" / "python"
    
    if python_path.is_file():
        return str(python_path)
    
    return sys.executable


def _read_process_output(
    pipe,
    output: bytearray,
    max_bytes: int = 10000,
) -> None:
    """Read process output while retaining only a limited amount."""

    while True:
        chunk = pipe.read(1024)

        if not chunk:
            break

        remaining = max_bytes - len(output)

        if remaining > 0:
            output.extend(chunk[:remaining])


def _terminate_process_tree(process: subprocess.Popen) -> None:
    """Terminate a process and its child processes."""

    if process.poll() is not None:
        return

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                timeout=10,
                shell=False,
                check=False,
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)

    except (OSError, subprocess.TimeoutExpired):
        pass

    if process.poll() is None:
        process.kill()


def _execute_tests(
    project_root: Path,
    command: list[str],
    timeout: int = 120,
) -> dict:
    """Execute tests with bounded output and timeout handling."""

    output = bytearray()
    process = None

    try:
        process = subprocess.Popen(
            command,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )

        reader = threading.Thread(
            target=_read_process_output,
            args=(process.stdout, output),
            daemon=True,
        )
        reader.start()

        try:
            return_code = process.wait(timeout=timeout)

        except subprocess.TimeoutExpired:
            _terminate_process_tree(process)
            process.wait()
            reader.join(timeout=5)

            if reader.is_alive():
                process.stdout.close()
                reader.join(timeout=1)

            return {
                "status": "timeout",
                "return_code": None,
                "output": output.decode("utf-8", errors="replace"),
            }

        reader.join()

        return {
            "status": "completed",
            "return_code": return_code,
            "output": output.decode("utf-8", errors="replace"),
        }

    except OSError as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()

        return {
            "status": "error",
            "return_code": None,
            "output": str(exc)[:10000],
        }



def run_tests(
    project_path: str,
    timeout: int = 120,
) -> dict:
    """Run detected Python tests in a project"""

    try:
        project_root = _validate_project_path(project_path)

        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise TypeError("Timeout must be an integer")
        
        if not 1<=timeout<=600:
            raise ValueError("Timeout must be between 1 and 600 seconds.")

        detection = _detect_test_framework(project_root)
        frameworks = detection["frameworks"]

        if not frameworks:
            return {
                "status": "not_found",
                "framework": None,
                "return_code": None,
                "output": "No supported test framework detected"
            }
        
        if "pytest" in frameworks:
            framework = "pytest"
            command = [
                _get_python_executable(project_root),
                "-m",
                "pytest",
                "-q",
            ]
        else:
            framework = "unittest"
            command = [
                _get_python_executable(project_root),
                "-m",
                "unittest",
                "discover",
            ]
        result = _execute_tests(
            project_root=project_root,
            command=command,
            timeout=timeout,
        )

        if result["status"] == "completed":
            status = (
                "passed"
                if result["return_code"] == 0
                else "failed"
            )
        else:
            status = result["status"]

        return {
            "status": status,
            "framework": framework,
            "return_code": result["return_code"],
            "output": result["output"],
        }

    except (ValueError, TypeError) as exc:
        return {
            "status": "error",
            "framework": None,
            "return_code": None,
            "output": str(exc),
        }

