import re
import builtins

MAX_TRACEBACK_SIZE_BYTES = 100_000

def _validate_error_input(error_text: str) -> str:
    """validate and normalize the supplied python error text"""

    if not isinstance(error_text, str):
        raise ValueError("Error input must be a string.")
    
    if not error_text.strip():
        raise ValueError("Error input cannot be empty.")
    
    if len(error_text.encode("utf-8")) > MAX_TRACEBACK_SIZE_BYTES:
        raise ValueError("Error input exceeds the 100 KB size limit.")
    
    return error_text.strip()



def _extract_exception(error_text: str) -> dict | None:
    """Extract the exception type and message."""

    lines = error_text.splitlines()

    for line in reversed(lines):
        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^([A-Za-z_][A-Za-z0-9_.]*)(?::\s*(.*))?$",
            line,
        )

        if not match:
            return None

        exception_type = match.group(1)
        message = match.group(2)

        # A colon indicates an exception name followed by a message.
        if message is None:
            # For exceptions without messages, accept known built-in
            # exception classes only.
            builtin_exception = getattr(
                builtins,
                exception_type,
                None,
            )

            if not (
                isinstance(builtin_exception, type)
                and issubclass(builtin_exception, BaseException)
            ):
                return None

            message = ""

        return {
            "type": exception_type,
            "message": message,
        }

    return None


def _extract_traceback_frames(error_text: str) -> list[dict]:
    """Extract file, line number, and function from traceback frames."""

    frame_pattern = re.compile(
        r'^\s*File "(.+)", line (\d+), in (.+)$'
    )

    frames = []

    for line in error_text.splitlines():
        match = frame_pattern.match(line)

        if match:
            frames.append({
                "filename": match.group(1),
                "line_number": int(match.group(2)),
                "function": match.group(3),
            })
    
    return frames


def analyze_error(error_text: str) -> dict:
    """Analyze Python errors and extract structured debugging information."""

    validated_text = _validate_error_input(error_text)

    exception = _extract_exception(validated_text)
    frames = _extract_traceback_frames(validated_text)

    error_location = frames[-1] if frames else None

    return {
        "exception": exception,
        "frames": frames,
        "error_location": error_location,
        "has_traceback": bool(frames)
    }