from typing import Any, cast

from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam, TextBlock, ToolParam, ToolUseBlock
from mcp import ClientSession

from lib.logger import setup_logger

logger = setup_logger(__name__)


class ClaudePlaywrightAgent:
    """Claude agent that orchestrates browser automation via MCP tools."""

    def __init__(self, api_key: str):
        logger.debug("Initializing Claude agent")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5"
        self.conversation_history: list[MessageParam] = []
        logger.debug(f"Using model: {self.model}")

    async def execute_task(
        self,
        task: str,
        mcp_session: ClientSession,
        max_iterations: int = 30,
    ) -> dict[str, Any]:
        """
        Execute a task using Claude + MCP tools in an agentic loop.

        This is the core pattern:
        1. Send task + available tools to Claude
        2. Claude responds with tool_use blocks
        3. Execute tools via MCP session
        4. Send results back to Claude
        5. Repeat until Claude returns final answer
        """

        logger.debug("Starting task execution")
        logger.debug(f"Task: {task[:200]}...")

        # Get available MCP tools and convert to Claude's tool format
        mcp_tools_response = await mcp_session.list_tools()
        tools = self._convert_mcp_tools_to_claude_format(mcp_tools_response.tools)
        logger.debug(f"Converted {len(tools)} MCP tools to Claude format")

        # Initialize conversation with user task
        self.conversation_history = [
            {
                "role": "user",
                "content": task,
            }
        ]

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"--- Iteration {iteration}/{max_iterations} ---")

            # Call Claude with current conversation + tools
            logger.debug("Calling Claude API...")
            response: Message = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=self.conversation_history,
                tools=cast(list[ToolParam], tools),
                thinking={"type": "enabled", "budget_tokens": 2000},
            )

            logger.info(f"Claude response - stop_reason: {response.stop_reason}")

            # Log thinking and reasoning blocks
            for block in response.content:
                block_type = getattr(block, 'type', None)
                if block_type in ("thinking", "text"):
                    content = getattr(block, 'thinking', None) or getattr(block, 'text', str(block))
                    logger.info(f"💭 Claude thinking: {content}")

            # Add assistant response to history
            self.conversation_history.append(
                {
                    "role": "assistant",
                    "content": response.content,
                }
            )

            # Check if Claude is done (no more tool calls)
            if response.stop_reason == "end_turn":
                # Extract final text response
                final_text = self._extract_text_from_response(response)
                logger.info("Claude finished with final response")
                logger.debug(f"Final text: {final_text[:200]}...")

                # Check if Claude is reporting a failure using the protocol
                if final_text.startswith("TASK_FAILED:"):
                    error_message = final_text.replace("TASK_FAILED:", "").strip()
                    logger.error(f"Claude reported task failure: {error_message}")
                    return {
                        "success": False,
                        "error": error_message,
                        "iterations": iteration,
                    }

                logger.info(f"Task completed successfully in {iteration} iterations")
                return {
                    "success": True,
                    "response": final_text,
                    "iterations": iteration,
                }

            # Process tool calls - execute ONE tool at a time for visibility
            if response.stop_reason == "tool_use":
                logger.debug("Claude requested tool calls")

                # Find first tool_use block
                tool_use_block = None
                for block in response.content:
                    if block.type == "tool_use":
                        tool_use_block = block
                        break

                if tool_use_block:
                    tool_name = tool_use_block.name
                    tool_input = tool_use_block.input
                    tool_use_id = tool_use_block.id

                    logger.info(f"Executing tool: {tool_name}")

                    try:
                        # Call MCP tool via session
                        result = await mcp_session.call_tool(
                            tool_name, arguments=cast(dict[str, Any], tool_input)
                        )

                        # Extract text content from MCP result
                        result_text = self._extract_mcp_result_text(result)

                        # Add tool result to conversation
                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": result_text,
                                    }
                                ],
                            }
                        )
                        logger.info(f"✓ {tool_name}")

                        # Check browser console for errors after each tool execution
                        try:
                            console_result = await mcp_session.call_tool(
                                "browser_console_messages",
                                arguments={"onlyErrors": True},
                            )
                            console_text = self._extract_mcp_result_text(console_result)
                            if console_text and console_text.strip():
                                logger.error(f"Browser console errors: {console_text}")
                        except Exception:
                            pass  # Ignore if browser_console_messages fails

                    except Exception as e:
                        logger.error(f"Tool execution error for {tool_name}: {e}")
                        self.conversation_history.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_id,
                                        "content": f"Error: {e!s}",
                                        "is_error": True,
                                    }
                                ],
                            }
                        )

                continue

            # Unexpected stop reason
            logger.error(f"Unexpected stop reason: {response.stop_reason}")
            return {
                "success": False,
                "error": f"Unexpected stop reason: {response.stop_reason}",
            }

        logger.error(f"Max iterations ({max_iterations}) exceeded")
        return {"success": False, "error": "Max iterations exceeded"}

    async def _execute_tool_calls(
        self,
        content: list[TextBlock | ToolUseBlock],
        mcp_session: ClientSession,
    ) -> list[dict[str, Any]]:
        """Execute tool_use blocks one at a time and return results."""
        tool_results = []

        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                logger.info(f"Executing tool: {tool_name}")
                logger.info(f"Tool input: {tool_input}")

                try:
                    # Call MCP tool via session
                    result = await mcp_session.call_tool(
                        tool_name, arguments=cast(dict[str, Any], tool_input)
                    )

                    # Extract text content from MCP result
                    result_text = self._extract_mcp_result_text(result)
                    logger.info(
                        f"Tool result (first 500 chars): {result_text[:500]}..."
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result_text,
                        }
                    )
                    logger.info(f"Tool {tool_name} executed successfully")

                except Exception as e:
                    logger.error(f"Tool execution error for {tool_name}: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Error: {e!s}",
                            "is_error": "true",
                        }
                    )
            elif block.type == "text":
                # Log any text/reasoning blocks
                logger.info(f"Claude text block: {block.text}")

        return tool_results

    def _convert_mcp_tools_to_claude_format(self, mcp_tools) -> list[dict]:
        """Convert MCP tool definitions to Claude's expected format."""
        claude_tools = []
        for tool in mcp_tools:
            claude_tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                }
            )
        return claude_tools

    def _extract_text_from_response(self, response: Message) -> str:
        """Extract text content from Claude's response."""
        text_parts = []
        for block in response.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _extract_mcp_result_text(self, mcp_result: Any) -> str:
        """Extract text from MCP tool result."""
        if hasattr(mcp_result, "content") and mcp_result.content:
            first_content = mcp_result.content[0]
            if hasattr(first_content, "text"):
                return str(first_content.text)
        return str(mcp_result)
