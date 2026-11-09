from pathlib import Path
import tomllib
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version
import httpx


MAX_MANIFEST_SIZE_BYTES = 1_000_000


def _validate_project_path(project_path: str) -> Path:
    """Validate the supplied project directory."""

    if not isinstance(project_path, str):
        raise ValueError("Project path must be a string.")

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


SUPPORTED_MANIFESTS = (
    "requirements.txt",
    "pyproject.toml",
)


def _discover_manifests(project_root: Path) -> list[Path]:
    """Find supported dependency manifest files in the project root."""

    if not project_root.is_dir():
        raise ValueError("Project root must be a directory.")

    manifests = []

    for filename in SUPPORTED_MANIFESTS:
        manifest_path = project_root / filename

        if manifest_path.is_symlink():
            raise ValueError(
                f"Symbolic links are not supported: {filename}"
            )

        if manifest_path.exists():
            if not manifest_path.is_file():
                raise ValueError(
                    f"Manifest must be a file: {filename}"
                )

            manifests.append(manifest_path)

    if not manifests:
        raise ValueError("No supported dependency manifest found.")

    return manifests


## Parse the requirements.txt file
def _parse_requirements_txt(manifest_path: Path) -> list[dict]:
    """Prase dependencies from a requirements.txt file"""

    dependencies = []

    content = manifest_path.read_text(encoding='utf-8')

    for line_number, line in enumerate(content.splitlines(), start=1):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        ## also skip pip options 
        if line.startswith("-"):
            continue

        try:
            requirement = Requirement(line)
        except Exception as exc:
            raise ValueError(
                f"Invalid dependency on line {line_number} : {line}"
            ) from exc
        
        dependencies.append({
            "name": requirement.name,
            "specifier": str(requirement.specifier)
        })

    return dependencies


## Parse the pyproject.toml file
def _parse_pyproject_toml(manifest_path: Path) -> list[dict]:
    """Prase dependencies from a pep 621 pyproject.toml file"""

    with manifest_path.open("rb") as file:
        data = tomllib.load(file)

    project = data.get("project", {})
    dependency_lines = list(project.get("dependencies",[]))

    optional_dependencies = project.get("optional-dependencies", {})

    for optional_group in optional_dependencies.values():
        dependency_lines.extend(optional_group)

    dependencies = []

    for line in dependency_lines:
        try:
            requirement =Requirement(line)
        except Exception as exc:
            raise ValueError(
                f"Invalid dependency declaration: {line}"
            ) from exc
        
        dependencies.append({
            "name": requirement.name,
            "specifier": str(requirement.specifier),
        })
    
    return dependencies


def _get_latest_version(package_name: str) -> dict:
    """Fetch the latest published package version from PyPI"""

    url = f"https://pypi.org/pypi/{package_name}/json"

    try:
        response = httpx.get(url, timeout=10)
    except httpx.TimeoutException:
        return {
            "latest_version": None,
            "status": "timeout",
        }
    except httpx.RequestError:
        return{
            "latest_version": None,
            "status": "network_error",
        }
    
    if response.status_code == 404:
        return{
            "latest_version": None,
            "status": "package_not_found",
        }
    
    try:
        response.raise_for_status()
        data = response.json()
        latest_version = data["info"]["version"]

        if not isinstance(latest_version, str) or not latest_version:
            raise ValueError("Invalid version returned by PyPI")
        
        return {
            "latest_version": latest_version,
            "status":"success",
        }
    except (httpx.HTTPStatusError, ValueError, KeyError, TypeError):
        return{
            "latest_version": None,
            "status": 'api_error',
        }
    

def _compare_versions(
    package_name: str,
    specifier: str,
    latest_version: str | None,
) -> dict:
    """Compare a declared exact version with the latest PyPI version."""

    declared_version = None

    # Only compare exact pinned versions for now.
    if specifier.startswith("==") and not specifier.startswith("==="):
        declared_version = specifier[2:]

    if latest_version is None:
        return {
            "name": package_name,
            "declared_version": declared_version,
            "latest_version": None,
            "update_available": None,
            "status": "version_unavailable",
        }

    if declared_version is None:
        return {
            "name": package_name,
            "declared_version": None,
            "latest_version": latest_version,
            "update_available": None,
            "status": "unpinned_version",
        }

    try:
        current = Version(declared_version)
        latest = Version(latest_version)

    except InvalidVersion:
        return {
            "name": package_name,
            "declared_version": declared_version,
            "latest_version": latest_version,
            "update_available": None,
            "status": "invalid_version",
        }

    return {
        "name": package_name,
        "declared_version": declared_version,
        "latest_version": latest_version,
        "update_available": latest > current,
        "status": "success",
    }


def _check_vulnerabilities(
    package_name: str,
    version: str | None,
) -> dict:
    """Check a python package version against the OSV database"""

    if not version:
        return {
            "vulnerabilities": [],
            "status": "version_unavailable",
        }
    
    url = "https://api.osv.dev/v1/query"

    payload = {
        "package": {
            "name": package_name,
            "ecosystem": "PyPI",
        },
        "version": version,
    }

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()
    
    except httpx.TimeoutException:
        return {
            "vulnerabilities": [],
            "status":"timeout",
        }
    except httpx.RequestError:
        return{
            "vulnerabilities": [],
            "status": "network_error"
        }
    except (httpx.HTTPStatusError, ValueError):
        return {
            "vulnerabilities": [],
            "status": "api_error",
        }
    
    vulnerabilities = []

    for vulnerability in data.get("vulns", []):
        vulnerabilities.append({
            "id": vulnerability.get("id"),
            "summary": vulnerability.get("summary"),
            "aliases": vulnerability.get("aliases",[]),
        })
    
    return {
        "vulnerabilities": vulnerabilities,
        "status": "success"
    }


def check_dependencies(project_path: str) -> dict:
    """Analyze project dependencies, latest versions, and known vulnerabilities"""

    project_root = _validate_project_path(project_path=project_path)
    manifest_paths = _discover_manifests(project_root)

    dependencies = []

    for manifest_path in manifest_paths:
        if manifest_path.stat().st_size > MAX_MANIFEST_SIZE_BYTES:
            raise ValueError(
                f"Manifest exceeds the 1 MB size limit : {manifest_path.name}"
            )
        
        try:
            if manifest_path.name == "requirements.txt":
                parsed = _parse_requirements_txt(manifest_path)
            else:
                parsed = _parse_pyproject_toml(manifest_path)
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise ValueError(
                f"Could not read manifest {manifest_path.name} : {exc}"
            ) from exc
        
        for dependency in parsed:
            dependencies.append({
                **dependency,
                "source": manifest_path.name
            })
        
    ## avoid checking the same package and version twice
    unique_dependencies = {}
    for dependency in dependencies:
        key = (
            dependency["name"].lower(),
            dependency["specifier"],
        )
        unique_dependencies.setdefault(key, dependency)
    
    results = []

    for dependency in unique_dependencies.values():
        name = dependency["name"]
        specifier = dependency["specifier"]

        pypi_result = _get_latest_version(name)

        version_result = _compare_versions(
            name, 
            specifier,
            pypi_result["latest_version"]
        )

        vulnerability_result = _check_vulnerabilities(
            name,
            version_result["declared_version"],
        )

        results.append({
            **version_result,
            "source": dependency["source"],
            "pypi_status": pypi_result["status"],
            "vulnerability_status": vulnerability_result["status"],
            "vulnerabilities": vulnerability_result["vulnerabilities"],
        })
    
    return {
        "project_path": str(project_path),
        "manifests": [path.name for path in manifest_paths],
        "total_dependencies": len(results),
        "dependencies": results,
    }