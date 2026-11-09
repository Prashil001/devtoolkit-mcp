import pytest

from devtoolkit_mcp.tools.analyze_error import _validate_error_input
from devtoolkit_mcp.tools.analyze_error import _extract_exception
from devtoolkit_mcp.tools.analyze_error import _extract_traceback_frames
from devtoolkit_mcp.tools.analyze_error import analyze_error


def test_accepts_valid_error_text():
    result = _validate_error_input(
        "ZeroDivisionError: division by zero"
    )

    assert result == "ZeroDivisionError: division by zero"


def test_removes_surrounding_whitespace():
    result = _validate_error_input(
        "  ValueError: Invalid input  "
    )

    assert result == "ValueError: Invalid input"


def test_rejects_empty_error_text():
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_error_input("")


def test_rejects_whitespace_only_input():
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_error_input("   ")


def test_rejects_non_string_input():
    with pytest.raises(ValueError, match="must be a string"):
        _validate_error_input(123)


def test_rejects_oversized_input():
    error_text = "A" * 100_001

    with pytest.raises(ValueError, match="100 KB"):
        _validate_error_input(error_text)


def test_extracts_exception_type_and_message():
    error = "ValueError: Invalid input"

    result = _extract_exception(error)

    assert result == {
        "type": "ValueError",
        "message": "Invalid input",
    }


def test_extracts_exception_without_message():
    error = "KeyboardInterrupt"

    result = _extract_exception(error)

    assert result == {
        "type": "KeyboardInterrupt",
        "message": "",
    }


def test_extracts_exception_from_traceback():
    error = """
Traceback (most recent call last):
  File "app.py", line 10, in calculate
    result = 10 / 0
ZeroDivisionError: division by zero
"""

    result = _extract_exception(error)

    assert result == {
        "type": "ZeroDivisionError",
        "message": "division by zero",
    }


def test_returns_none_when_exception_is_missing():
    error = "This is not a Python traceback."

    result = _extract_exception(error)

    assert result is None


def test_extracts_dotted_exception_name():
    error = "requests.exceptions.ConnectionError: Connection failed"

    result = _extract_exception(error)

    assert result == {
        "type": "requests.exceptions.ConnectionError",
        "message": "Connection failed",
    }


def test_extracts_single_traceback_frame():
    error = '''
Traceback (most recent call last):
  File "app.py", line 10, in calculate
ZeroDivisionError: division by zero
'''

    result = _extract_traceback_frames(error)

    assert result == [
        {
            "filename": "app.py",
            "line_number": 10,
            "function": "calculate",
        }
    ]


def test_extracts_multiple_traceback_frames():
    error = '''
Traceback (most recent call last):
  File "main.py", line 15, in main
    calculate()
  File "calculator.py", line 8, in calculate
    return 10 / 0
ZeroDivisionError: division by zero
'''

    result = _extract_traceback_frames(error)

    assert len(result) == 2
    assert result[0]["filename"] == "main.py"
    assert result[0]["line_number"] == 15
    assert result[1]["filename"] == "calculator.py"
    assert result[1]["line_number"] == 8


def test_returns_empty_list_without_traceback_frames():
    error = "ValueError: Invalid input"

    result = _extract_traceback_frames(error)

    assert result == []


def test_extracts_frame_with_windows_path():
    error = '''
Traceback (most recent call last):
  File "D:\\projects\\app.py", line 25, in main
ValueError: Invalid input
'''

    result = _extract_traceback_frames(error)

    assert len(result) == 1
    assert result[0]["filename"] == "D:\\projects\\app.py"
    assert result[0]["line_number"] == 25


def test_analyze_error_with_complete_traceback():
    error = '''
Traceback (most recent call last):
  File "main.py", line 15, in main
    calculate()
  File "calculator.py", line 8, in calculate
    return 10 / 0
ZeroDivisionError: division by zero
'''

    result = analyze_error(error)

    assert result["exception"]["type"] == "ZeroDivisionError"
    assert result["exception"]["message"] == "division by zero"

    assert len(result["frames"]) == 2

    assert result["error_location"] == {
        "filename": "calculator.py",
        "line_number": 8,
        "function": "calculate",
    }

    assert result["has_traceback"] is True


def test_analyze_error_with_plain_exception():
    error = "ValueError: Invalid input"

    result = analyze_error(error)

    assert result["exception"] == {
        "type": "ValueError",
        "message": "Invalid input",
    }

    assert result["frames"] == []
    assert result["error_location"] is None
    assert result["has_traceback"] is False


def test_analyze_error_with_unrecognized_text():
    error = "This is not a Python traceback."

    result = analyze_error(error)

    assert result["exception"] is None
    assert result["frames"] == []
    assert result["error_location"] is None
    assert result["has_traceback"] is False


def test_analyze_error_rejects_empty_input():
    with pytest.raises(ValueError, match="cannot be empty"):
        analyze_error("")

def test_does_not_recognize_arbitrary_word_as_exception():
    result = _extract_exception("hello")

    assert result is None


def test_recognizes_builtin_exception_without_message():
    result = _extract_exception("KeyboardInterrupt")

    assert result == {
        "type": "KeyboardInterrupt",
        "message": "",
    }