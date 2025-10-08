import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from lib.logger import setup_logger

logger = setup_logger(__name__)


class MCPPlaywrightClient:
    """Manages connection to Playwright MCP server via stdio."""

    def __init__(self, user_data_dir: str | None = None):
        logger.info(f"Initializing MCP client: user_data_dir={user_data_dir}")

        # Get path to stealth script
        stealth_script = os.path.join(os.path.dirname(__file__), "stealth.js")

        args = [
            "--offline",  # Use cached package only, no network calls
            "--yes",  # Skip install prompt
            "@playwright/mcp@latest",
            "--browser=firefox",  # Firefox works on ARM64, Chromium doesn't
            "--headless",
            "--caps=tracing",
            "--save-trace",
            f"--output-dir={user_data_dir}",
            "--no-sandbox",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:133.0) Gecko/20100101 Firefox/133.0",
            f"--init-script={stealth_script}",
            # "--port=8931", # for sse mode according to docs, but not needed for stdio, to accomodate headed browsers on systems without display
            # see: https://github.com/microsoft/playwright-mcp/blob/ce7236720874e55e9055c191aa16f440d9204346/README.md#standalone-mcp-server
        ]

        if user_data_dir:
            args.append(f"--user-data-dir={user_data_dir}")

        logger.info(f"MCP server command: npx {' '.join(args)}")

        self.server_params = StdioServerParameters(
            command="npx",
            args=args,
        )
        self.user_data_dir = user_data_dir

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[ClientSession]:
        """Establish stdio connection to Playwright MCP server."""
        logger.info("Connecting to Playwright MCP server via stdio...")
        async with (
            stdio_client(self.server_params) as (read, write),
            ClientSession(read, write) as session,
        ):
            logger.info("Initializing MCP session...")
            await session.initialize()

            # List available tools for debugging
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            logger.info(f"MCP session initialized. Available tools: {tool_names}")

            yield session

            logger.info("Closing MCP session")
