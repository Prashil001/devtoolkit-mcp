from fastmcp import FastMCP

from devtoolkit_mcp.tools.repository import analyze_repository
from devtoolkit_mcp.tools.explain_code import explain_code

mcp = FastMCP("DevToolKit MCP")

mcp.tool(analyze_repository)
mcp.tool(explain_code)


def main():
    """Main entry point for the DevToolKit MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()