#!/usr/bin/env python3
"""
YouTube MCP Server Starter
Launch the MCP server with proper environment setup.
"""

import subprocess
import sys
import os


def main():
    """Start the YouTube MCP server"""
    print("🎬 Starting YouTube MCP Server...")

    # Check if we're in the right directory
    if not os.path.exists("youtube_mcp_server_fastmcp.py"):
        print("❌ Error: youtube_mcp_server_fastmcp.py not found in current directory")
        print("Please run this from the youtube_download directory")
        sys.exit(1)

    # Import and run the FastMCP server directly
    # MCP servers run in the same process and communicate via stdio
    try:
        import youtube_mcp_server_fastmcp
        # This will run the server and never return - it waits for stdio input
        youtube_mcp_server_fastmcp.main()
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

