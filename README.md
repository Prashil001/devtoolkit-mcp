# DevToolkit MCP

**A lightweight, model-independent MCP server that gives AI assistants practical software development tools.**

[![PyPI version](https://img.shields.io/pypi/v/devtoolkit-mcp)](https://pypi.org/project/devtoolkit-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/devtoolkit-mcp)](https://pypi.org/project/devtoolkit-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/Prashil001/devtoolkit-mcp)

DevToolkit MCP is an open-source **Model Context Protocol (MCP) server** that exposes essential software development utilities as tools that AI assistants can call.

It helps AI assistants inspect Python projects, understand code, analyze errors, check dependencies, and execute tests through a standardized MCP interface.

The server is designed to be simple, extensible, and independent of any specific AI model or provider.

## Features

- **Repository Analysis:** Inspect project structure, file types, and configuration files.
- **Code Explanation:** Analyze Python code using Abstract Syntax Trees (AST).
- **Error Analysis:** Extract useful information from Python exceptions and tracebacks.
- **Dependency Checking:** Identify dependency versions and check for known vulnerabilities.
- **Test Execution:** Detect and execute pytest or unittest test suites.
- **MCP Integration:** Connect compatible AI assistants through the Model Context Protocol.
- **Model Independent:** Works with MCP-compatible clients without requiring a specific LLM provider.

## Available Tools

DevToolkit MCP currently provides five tools.

### 1. `analyze_repository`

Analyzes a local project directory and returns information about its structure.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `repository_path` | string | Required | Path to the project directory |
| `max_files` | integer | 5000 | Maximum number of files to inspect |

**Returns**

- Project directory information
- File and directory statistics
- File extension distribution
- Detected languages and configuration files
- Project structure information

### 2. `explain_code`

Analyzes Python source code or a Python file using AST parsing.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `code` | string or null | None | Python source code |
| `file_path` | string or null | None | Path to a Python file |

Provide either `code` or `file_path`.

**Returns**

- Functions and classes
- Methods and imports
- Code structure and statistics
- Syntax errors, when present

### 3. `analyze_error`

Analyzes Python exceptions and traceback text.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `error_text` | string | Python exception or traceback |

**Returns**

- Exception type
- Error message
- File and line information, when available
- Traceback details
- Structured error information

### 4. `check_dependencies`

Checks project dependencies and retrieves package information from external vulnerability and package registries.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `project_path` | string | Path to the Python project |

**Supported dependency files**

- `requirements.txt`
- `pyproject.toml`

**Returns**

- Detected dependencies
- Declared dependency versions
- Latest available versions from PyPI
- Known vulnerability information from OSV, when available

Network access is required for live PyPI and OSV checks. Network failures are handled without treating unavailable data as a clean security result.

### 5. `run_tests`

Automatically detects and executes Python test suites.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `project_path` | string | Required | Path to the project directory |
| `timeout` | integer | 120 | Maximum execution time in seconds (1–600) |

**Supported frameworks**

- pytest
- unittest

**Returns**

- Detected testing framework
- Test execution status
- Process exit code
- Test output
- Timeout or execution error information, when applicable

The tool prefers pytest when both frameworks are detected and uses the project's virtual environment when available.

---

## Installation

### Using uv (recommended)

```bash
uv tool install devtoolkit-mcp
```

Alternatively, run it without permanently installing:

```bash
uvx devtoolkit-mcp
```

### Using pip

```bash
pip install devtoolkit-mcp
```

## MCP Client Configuration

Add DevToolkit MCP to an MCP-compatible client.

### Claude Desktop

Open your Claude Desktop configuration file and add:

```json
{
  "mcpServers": {
    "devtoolkit-mcp": {
      "command": "uvx",
      "args": ["devtoolkit-mcp"]
    }
  }
}
```

Restart Claude Desktop after saving the configuration.

### Other MCP-compatible clients

Use the following command to launch the server:

```bash
uvx devtoolkit-mcp
```

Configure your client to launch this command using its supported MCP transport configuration.

## Example Use Cases

Once connected to an MCP-compatible AI assistant, you can ask it to:

- "Analyze the structure of my Python project."
- "Explain the classes and functions in this Python file."
- "Analyze this traceback and identify the exception."
- "Check my project's dependencies for outdated or vulnerable packages."
- "Run the tests in my project and show me the results."

The AI assistant decides when to invoke the available tools based on the user's request and the MCP client.

## Architecture

```text
          AI Assistant
                |
                |
        MCP-Compatible Client
                |
                |
         DevToolkit MCP
                |
       +--------+--------+
       |        |        |
       v        v        v
  Repository  Code     Error
  Analysis   Analysis  Analysis
       |
       +----------------+
       |                |
       v                v
  Dependency          Test
   Checking         Execution
```

DevToolkit MCP uses the Model Context Protocol to expose development utilities through standardized tool interfaces.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Core implementation |
| FastMCP | MCP server and tool registration |
| AST | Python source code analysis |
| httpx | HTTP requests to external APIs |
| packaging | Python dependency version parsing |
| pytest | Automated testing |
| Ruff | Linting and formatting |
| uv | Python project and package management |

## Project Structure

```text
devtoolkit-mcp/
│
├── src/
│   └── devtoolkit_mcp/
│       ├── tools/
│       │   ├── repository.py
│       │   ├── explain_code.py
│       │   ├── analyze_error.py
│       │   ├── check_dependencies.py
│       │   └── run_tests.py
│       │
│       └── server.py
│
├── tests/
│
├── .github/
│   └── workflows/
│       └── publish.yml
│
├── LICENSE
├── README.md
├── pyproject.toml
└── uv.lock
```

## Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/Prashil001/devtoolkit-mcp.git
cd devtoolkit-mcp
```

### 2. Install dependencies

```bash
uv sync --dev
```

### 3. Run tests

```bash
uv run pytest -v
```

### 4. Run linting

```bash
uv run ruff check .
```

### 5. Check formatting

```bash
uv run ruff format --check .
```

### 6. Run the MCP server

```bash
uv run devtoolkit-mcp
```

## Security Considerations

- Repository inspection is restricted to validated local project directories.
- Test execution uses subprocesses without shell command interpretation.
- Test execution has a configurable timeout.
- Dependency vulnerability checks use external public APIs.
- Tool execution should only be allowed on project directories the user trusts.
- Do not expose sensitive project files or credentials to AI clients unnecessarily.

## Contributing

Contributions, bug reports, and feature suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Add or update tests.
5. Run the test suite and Ruff checks.
6. Submit a pull request.

Please keep contributions focused on improving the existing five tools unless the project scope is explicitly expanded.

## License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for details.

## Author

**Prashil001**

- GitHub: https://github.com/Prashil001
- Repository: https://github.com/Prashil001/devtoolkit-mcp

---

If you find DevToolkit MCP useful, consider giving the repository a ⭐ on GitHub.

**Built to make AI-assisted software development more capable through MCP.**