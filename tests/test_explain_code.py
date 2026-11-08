import pytest
import ast

from devtoolkit_mcp.tools.explain_code import _extract_functions
from devtoolkit_mcp.tools.explain_code import _extract_classes
from devtoolkit_mcp.tools.explain_code import _extract_imports
from devtoolkit_mcp.tools.explain_code import _calculate_statistics
from devtoolkit_mcp.tools.explain_code import explain_code
from devtoolkit_mcp.tools.explain_code import (
    MAX_SOURCE_SIZE_BYTES,
    _load_source_code,
)


def test_load_source_code_from_snippet():
    code = "def add(a, b): return a + b"

    source, source_type = _load_source_code(code, None)

    assert source == code
    assert source_type == "code_snippet"


def test_load_source_code_from_file(tmp_path):
    file_path = tmp_path / "example.py"
    file_path.write_text("print('hello')", encoding="utf-8")

    source, source_type = _load_source_code(
        None,
        str(file_path),
    )

    assert source == "print('hello')"
    assert source_type == "file"


def test_rejects_missing_inputs():
    with pytest.raises(ValueError, match="Provide either"):
        _load_source_code(None, None)


def test_rejects_both_inputs():
    with pytest.raises(ValueError, match="Provide either"):
        _load_source_code("print('hello')", "example.py")


def test_rejects_empty_code():
    with pytest.raises(ValueError, match="empty"):
        _load_source_code("   ", None)


def test_rejects_oversized_code():
    code = "a" * (MAX_SOURCE_SIZE_BYTES + 1)

    with pytest.raises(ValueError, match="1 MB"):
        _load_source_code(code, None)


def test_rejects_nonexistent_file(tmp_path):
    file_path = tmp_path / "missing.py"

    with pytest.raises(ValueError, match="does not exist"):
        _load_source_code(None, str(file_path))


def test_rejects_non_python_file(tmp_path):
    file_path = tmp_path / "example.txt"
    file_path.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="Python"):
        _load_source_code(None, str(file_path))


def test_rejects_directory(tmp_path):
    directory = tmp_path / "example.py"
    directory.mkdir()

    with pytest.raises(ValueError, match="regular file"):
        _load_source_code(None, str(directory))


def test_rejects_oversized_file(tmp_path):
    file_path = tmp_path / "large.py"
    file_path.write_bytes(b"a" * (MAX_SOURCE_SIZE_BYTES + 1))

    with pytest.raises(ValueError, match="1 MB"):
        _load_source_code(None, str(file_path))


def test_rejects_invalid_utf8_file(tmp_path):
    file_path = tmp_path / "invalid.py"
    file_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ValueError, match="UTF-8"):
        _load_source_code(None, str(file_path))


def test_extracts_normal_function():
    code = """
def calculate_total(price, quantity):
    return price * quantity
"""

    tree = ast.parse(code)
    functions = _extract_functions(tree)

    assert len(functions) == 1
    assert functions[0]["name"] == "calculate_total"
    assert functions[0]["arguments"] == ["price", "quantity"]
    assert functions[0]["line_number"] == 2
    assert functions[0]["is_async"] is False


def test_extracts_async_function():
    code = """
async def fetch_user(user_id):
    pass
"""

    tree = ast.parse(code)
    functions = _extract_functions(tree)

    assert len(functions) == 1
    assert functions[0]["name"] == "fetch_user"
    assert functions[0]["arguments"] == ["user_id"]
    assert functions[0]["is_async"] is True


def test_extracts_function_docstring():
    code = '''
def greet(name):
    """Greet a user by name."""
    return f"Hello {name}"
'''

    tree = ast.parse(code)
    functions = _extract_functions(tree)

    assert functions[0]["docstring"] == "Greet a user by name."


def test_extracts_advanced_function_arguments():
    code = """
def example(a, /, b, *args, c, **kwargs):
    pass
"""

    tree = ast.parse(code)
    functions = _extract_functions(tree)

    assert functions[0]["arguments"] == [
        "a",
        "b",
        "*args",
        "c",
        "**kwargs",
    ]


def test_ignores_nested_functions():
    code = """
def outer():
    def inner():
        pass
"""

    tree = ast.parse(code)
    functions = _extract_functions(tree)

    assert len(functions) == 1
    assert functions[0]["name"] == "outer"


def test_extracts_class():
    source = """
class Student:
    pass
"""
    tree = ast.parse(source)

    result = _extract_classes(tree)

    assert len(result) == 1
    assert result[0]["name"] == "Student"
    assert result[0]["line_number"] == 2


def test_extracts_class_docstring():
    source = '''
class Student:
    """Represents a student."""
'''
    tree = ast.parse(source)

    result = _extract_classes(tree)

    assert result[0]["docstring"] == "Represents a student."


def test_extracts_class_methods():
    source = """
class Student:
    def study(self):
        pass

    def sleep(self, hours):
        pass
"""
    tree = ast.parse(source)

    result = _extract_classes(tree)

    assert len(result[0]["methods"]) == 2
    assert result[0]["methods"][0]["name"] == "study"
    assert result[0]["methods"][1]["name"] == "sleep"
    assert result[0]["methods"][1]["arguments"] == [
        "self",
        "hours",
    ]


def test_extracts_async_class_method():
    source = """
class Student:
    async def study(self):
        pass
"""
    tree = ast.parse(source)

    result = _extract_classes(tree)

    assert result[0]["methods"][0]["name"] == "study"
    assert result[0]["methods"][0]["is_async"] is True


def test_ignores_nested_classes():
    source = """
class Student:
    class Details:
        pass
"""
    tree = ast.parse(source)

    result = _extract_classes(tree)

    assert len(result) == 1
    assert result[0]["name"] == "Student"


def test_extracts_regular_import():
    source = "import os"
    tree = ast.parse(source)

    result = _extract_imports(tree)

    assert len(result) == 1
    assert result[0]["type"] == "import"
    assert result[0]["name"] == "os"
    assert result[0]["module"] is None


def test_extracts_import_alias():
    source = "import pandas as pd"
    tree = ast.parse(source)

    result = _extract_imports(tree)

    assert result[0]["name"] == "pandas"
    assert result[0]["alias"] == "pd"


def test_extracts_from_import():
    source = "from pathlib import Path"
    tree = ast.parse(source)

    result = _extract_imports(tree)

    assert result[0]["type"] == "from_import"
    assert result[0]["module"] == "pathlib"
    assert result[0]["name"] == "Path"


def test_extracts_multiple_imported_names():
    source = "from fastapi import FastAPI, HTTPException"
    tree = ast.parse(source)

    result = _extract_imports(tree)

    assert len(result) == 2
    assert result[0]["name"] == "FastAPI"
    assert result[1]["name"] == "HTTPException"


def test_extracts_relative_import():
    source = "from .utils import helper"
    tree = ast.parse(source)

    result = _extract_imports(tree)

    assert result[0]["module"] == "utils"
    assert result[0]["name"] == "helper"
    assert result[0]["level"] == 1


def test_ignores_nested_imports():
    source = """
def load():
    import os
"""
    tree = ast.parse(source)

    result = _extract_imports(tree)

    assert result == []

def test_calculates_code_statistics():
    source = '''import os

def greet(name):
    return f"Hello {name}"

class Student:
    pass
'''

    tree = ast.parse(source)

    result = _calculate_statistics(source, tree)

    assert result == {
        "total_lines": 7,
        "function_count": 1,
        "class_count": 1,
        "import_count": 1,
    }


def test_calculates_statistics_for_empty_module():
    source = ""
    tree = ast.parse(source)

    result = _calculate_statistics(source, tree)

    assert result == {
        "total_lines": 0,
        "function_count": 0,
        "class_count": 0,
        "import_count": 0,
    }


def test_counts_multiple_imported_names():
    source = "from pathlib import Path, PurePath"
    tree = ast.parse(source)

    result = _calculate_statistics(source, tree)

    assert result["import_count"] == 2


def test_explain_code_with_valid_python():
    source = """
import os

def greet(name):
    return f"Hello {name}"

class Student:
    def study(self):
        pass
"""

    result = explain_code(code=source)

    assert result["syntax_valid"] is True
    assert result["source_type"] == "code_snippet"
    assert result["language"] == "Python"
    assert len(result["functions"]) == 1
    assert len(result["classes"]) == 1
    assert len(result["imports"]) == 1
    assert result["syntax_error"] is None


def test_explain_code_with_invalid_python():
    source = """
def greet(
    print("Hello")
"""

    result = explain_code(code=source)

    assert result["syntax_valid"] is False
    assert result["functions"] == []
    assert result["classes"] == []
    assert result["imports"] == []
    assert result["statistics"] is None
    assert result["syntax_error"] is not None
    assert result["syntax_error"]["line_number"] is not None


def test_explain_code_rejects_empty_input():
    with pytest.raises(ValueError, match="Provided code is empty"):
        explain_code(code="")