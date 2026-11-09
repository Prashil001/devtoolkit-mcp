from fastmcp import FastMCP

from devtoolkit_mcp.tools.repository import analyze_repository
from devtoolkit_mcp.tools.explain_code import explain_code
from devtoolkit_mcp.tools.analyze_error import analyze_error
from devtoolkit_mcp.tools.check_dependencies import check_dependencies

mcp = FastMCP("DevToolKit MCP")

mcp.tool(analyze_repository)
mcp.tool(explain_code)
mcp.tool(analyze_error)
mcp.tool(check_dependencies)


def main():
    """Main entry point for the DevToolKit MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()