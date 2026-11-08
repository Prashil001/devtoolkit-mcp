import stat
from pathlib import Path
import ast


MAX_SOURCE_SIZE_BYTES = 1_100_000  # 1.1 MB

def _load_source_code(
    code: str | None,
    file_path: str | None,
) -> tuple[str, str]:
    
    if (code is None) == (file_path is None):
        raise ValueError("Provide either code or file_path, but not both." 
        )
    
    if code is not None:
        if not code.strip():
            raise ValueError("Provided code is empty.")

        if len(code.encode("utf-8")) > MAX_SOURCE_SIZE_BYTES:
            raise ValueError("Provided code exceeds the maximum allowed size of 1.1 MB.")
        
        return code, "code_snippet"
    
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise ValueError(f"File path does not exist: {path}")
    
    if path.is_symlink():
        raise ValueError(f"File path is a symbolic link: {path}")
    
    if path.suffix.lower() != ".py":
        raise ValueError(f"File path does not point to a Python file: {path}")
    
    file_stat = path.stat()

    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError(f"File path is not a regular file: {path}")
    
    if file_stat.st_size > MAX_SOURCE_SIZE_BYTES:
        raise ValueError("File size exceeds the maximum allowed size of 1.1 MB.")

    try:
        source_code = path.read_text(encoding="utf-8")
    
    except UnicodeDecodeError as exc:
        raise ValueError(f"File path is not a valid UTF-8 encoded text file: {path}") from exc
    
    return source_code, "file"
        
def _extract_functions(tree: ast.Module) -> list[dict]:
    """extract top level functions from a python AST"""
    
    functions = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = [
                argument.arg
                for argument in (
                    node.args.posonlyargs + node.args.args
                )
            ]

            if node.args.vararg:
                arguments.append(f"*{node.args.vararg.arg}")

            arguments.extend(
                argument.arg for argument in node.args.kwonlyargs
            )

            if node.args.kwarg:
                arguments.append(f"**{node.args.kwarg.arg}")
            
            functions.append({
                "name": node.name,
                "arguments": arguments,
                "line_number": node.lineno,
                "docstring": ast.get_docstring(node),
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })

    return functions


def _extract_classes(tree: ast.Module) -> list[dict]:
    """Extract top-level classes and their methods from Python AST."""

    classes = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = []

            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    arguments = [
                        argument.arg
                        for argument in (
                            child.args.posonlyargs
                            + child.args.args
                        )
                    ]

                    if child.args.vararg:
                        arguments.append(f"*{child.args.vararg.arg}")

                    arguments.extend(
                        argument.arg
                        for argument in child.args.kwonlyargs
                    )

                    if child.args.kwarg:
                        arguments.append(f"**{child.args.kwarg.arg}")

                    methods.append({
                        "name": child.name,
                        "arguments": arguments,
                        "line_number": child.lineno,
                        "docstring": ast.get_docstring(child),
                        "is_async": isinstance(
                            child,
                            ast.AsyncFunctionDef,
                        ),
                    })

            classes.append({
                "name": node.name,
                "line_number": node.lineno,
                "docstring": ast.get_docstring(node),
                "methods": methods,
            })

    return classes


def _extract_imports(tree: ast.Module) -> list[dict]:
    """Extract top-level imports from python AST"""

    imports = []

    for node in tree.body:
        if isinstance(node,ast.Import):
            for alias in node.names:
                imports.append({
                    "type":"import",
                    "module": None,
                    "name": alias.name,
                    "alias": alias.asname,
                    "level": 0,
                    "line_number": node.lineno,
                })
        
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append({
                    "type":"from_import",
                    "module":node.module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "level": node.level,
                    "line_number": node.lineno,
                })
    return imports


def _calculate_statistics(
    source_code: str,
    tree: ast.Module,
) -> dict:

    """Calculate basic statistics for python source code."""

    functions = _extract_functions(tree)
    classes = _extract_classes(tree)
    imports = _extract_imports(tree)

    return {
        "total_lines": len(source_code.splitlines()),
        "function_count": len(functions),
        "class_count": len(classes),
        "import_count": len(imports)
    }


def explain_code(
    code: str | None = None,
    file_path: str | None = None,
) -> dict:
    """Analyze Python code and explain its basic structure."""

    source_code, source_type = _load_source_code(
        code=code,
        file_path=file_path,
    )

    try:
        tree = ast.parse(source_code)

    except SyntaxError as exc:
        return {
            "source_type": source_type,
            "language": "Python",
            "syntax_valid": False,
            "functions": [],
            "classes": [],
            "imports": [],
            "statistics": None,
            "syntax_error": {
                "message": exc.msg,
                "line_number": exc.lineno,
                "column": exc.offset,
            },
        }

    return {
        "source_type": source_type,
        "language": "Python",
        "syntax_valid": True,
        "functions": _extract_functions(tree),
        "classes": _extract_classes(tree),
        "imports": _extract_imports(tree),
        "statistics": _calculate_statistics(
            source_code,
            tree,
        ),
        "syntax_error": None,
    }