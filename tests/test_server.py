import asyncio
from pathlib import Path

from fastmcp import Client

from devtoolkit_mcp.server import mcp


def test_server_registers_all_five_tools():
    async def check_tools():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            return {tool.name for tool in tools}

    tool_names = asyncio.run(check_tools())

    expected_tools = {
        "analyze_repository",
        "explain_code",
        "analyze_error",
        "check_dependencies",
        "run_tests",
    }

    assert tool_names == expected_tools


def test_server_executes_analyze_error():
    async def check_tool():
        async with Client(mcp) as client:
            result = await client.call_tool(
                "analyze_error",
                {
                    "error_text": "ValueError: invalid input",
                },
            )
            return result

    result = asyncio.run(check_tool())

    assert result is not None

def test_server_executes_analyze_repository(tmp_path):
    async def check_tool():
        async with Client(mcp) as client:
            return await client.call_tool(
                "analyze_repository",
                {"repository_path": str(tmp_path)},
            )

    result = asyncio.run(check_tool())
    assert result is not None

def test_server_executes_explain_code():
    async def check_tool():
        async with Client(mcp) as client:
            return await client.call_tool(
                "explain_code",
                {"code": "def greet():\n    return 'Hello'"},
            )

    result = asyncio.run(check_tool())
    assert result is not None

def test_server_executes_check_dependencies(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "requests==2.31.0\n",
        encoding="utf-8",
    )

    async def check_tool():
        async with Client(mcp) as client:
            return await client.call_tool(
                "check_dependencies",
                {"project_path": str(tmp_path)},
            )

    result = asyncio.run(check_tool())
    assert result is not None

def test_server_executes_run_tests(tmp_path):
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\n",
        encoding="utf-8",
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_sample.py").write_text(
        "def test_example():\n    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )

    async def check_tool():
        async with Client(mcp) as client:
            return await client.call_tool(
                "run_tests",
                {"project_path": str(tmp_path)},
            )

    result = asyncio.run(check_tool())
    assert result is not None



