import os
from collections import Counter
from pathlib import Path

IGNORED_DIRECTORIES = {
    ".git", 
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".dist",
    "build",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
}

def analyze_repository(
    repository_path: str,
    max_files: int = 5000,
) -> dict:
    """
    Analyze the repository at the given path and return a summary of its contents.

    Args:
        repository_path (str): The path to the repository.
        max_files (int): The maximum number of files to analyze.

    Returns:
        dict: A summary of the repository's contents, including total files, 
              total lines of code, and a breakdown of file types.
    """
    
    if max_files < 1 or max_files > 20000:
        raise ValueError("max_files must be between 1 and 20000.")
    
    root = Path(repository_path).expanduser().resolve()

    if not root.exists():
        raise ValueError(f"Repository path does not exist:{root}")

    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    language_counts = Counter()
    configuration_files = []
    directory_count = 0
    files_scanned = 0
    truncated = False

    important_files = {
        "pyproject.toml",
        "requirements.txt",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "Dockerfile",
        "docker-compose.yml",
        "alembic.ini",
        "pytest.ini",
        "README.md",
    }

    top_level_entries = sorted(
        entry.name for entry in root.iterdir() if entry.is_dir() and entry.name not in IGNORED_DIRECTORIES
    )

    for current_root, directories, files in os.walk(
        root,
        followlinks=False,
    ):
        directories[:] = [
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not (Path(current_root) / directory).is_symlink()
        ]

        directory_count += len(directories)

        for filename in files:
            file_path = Path(current_root) / filename

            if file_path.is_symlink():
                continue

            if files_scanned >= max_files:
                truncated = True
                break

            files_scanned += 1

            extension = file_path.suffix.lower()

            if extension in LANGUAGE_EXTENSIONS:
                language_counts[LANGUAGE_EXTENSIONS[extension]] += 1
            
            if filename in important_files:
                configuration_files.append(str(file_path.relative_to(root)))
        

        if truncated:
            break


    return {
        "project_name": root.name,
        "repository_path": str(root),
        "files_scanned": files_scanned,
        "directories": directory_count,
        "languages": dict(language_counts.most_common()),
        "important_files": sorted(configuration_files),
        "top_level_entries": top_level_entries,
        "truncated": truncated,
    }
    
