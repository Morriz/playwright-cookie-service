import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPPlaywrightClient:
    """Manages connection to Playwright MCP server via stdio."""

    def __init__(self, browser: str = "chromium"):
        logger.info(f"Initializing MCP client: browser={browser}")

        # Get path to stealth script
        stealth_script = os.path.join(os.path.dirname(__file__), "stealth.js")

        args = [
            "@playwright/mcp@latest",
            f"--browser={browser}",
            "--isolated",
            "--no-sandbox",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            f"--init-script={stealth_script}",
        ]

        logger.info(f"MCP server command: npx {' '.join(args)}")

        self.server_params = StdioServerParameters(
            command="npx",
            args=args,
        )

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[ClientSession]:
        """Establish stdio connection to Playwright MCP server."""
        logger.info("Connecting to Playwright MCP server via stdio...")
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                logger.info("Initializing MCP session...")
                await session.initialize()

                # List available tools for debugging
                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools]
                logger.info(f"MCP session initialized. Available tools: {tool_names}")

                yield session

                logger.info("Closing MCP session")
