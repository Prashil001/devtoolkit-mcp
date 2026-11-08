from fastmcp import FastMCP

from devtoolkit_mcp.tools.repository import analyze_repository

mcp = FastMCP("DevToolKit MCP")

mcp.tool(analyze_repository)


def main():
    """Main entry point for the DevToolKit MCP server"""
    mcp.run()

if __name__ == "__main__":
    main()