import os
import sys
import uuid

import httpx
from claude_agent import ClaudePlaywrightAgent
from fastapi import BackgroundTasks, FastAPI, HTTPException
from mcp_client import MCPPlaywrightClient
from models import CookieRequest, CookieResponse, TaskStatusResponse, WebhookPayload

sys.path.insert(0, str(os.path.dirname(os.path.dirname(__file__))))
from logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="X Cookie Service")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


async def process_cookie_request(
    request: CookieRequest, request_id: str, webhook_url: str
):
    """
    Background task to process cookie retrieval and send webhook.
    """
    logger.info(
        f"[{request_id}] Processing cookie request for X username: {request.x_username}"
    )

    # Get Anthropic API key from environment
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not configured")
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        logger.info("Initializing Claude agent and MCP client")
        # Initialize Claude agent
        agent = ClaudePlaywrightAgent(api_key=anthropic_api_key)

        # Initialize MCP Playwright client
        # Use headed mode with Xvfb in Docker (virtual display)
        mcp_client = MCPPlaywrightClient(browser="chromium")

        # Connect to Playwright MCP and execute task
        logger.info("Connecting to Playwright MCP server")
        async with mcp_client.connect() as session:
            # Construct task for Claude
            task = f"""
You are a browser automation expert. Your task is to log in to X (Twitter) and retrieve all cookies.

Credentials:
- X Username: {request.x_username}
- X Email: {request.x_email}
- X Password: {request.x_password}
- ProtonMail Email: {request.protonmail_email}
- ProtonMail Password: {request.protonmail_password}

Steps to follow:
1. Navigate to https://x.com/login
2. Enter the username and submit
3. If asked for email/phone verification, enter the email
4. Enter the password and submit
5. If a verification code is required:
   a. Open https://account.proton.me/login in a new tab or navigate to it
   b. Log in to ProtonMail with the provided credentials
   c. Find the latest email from X/Twitter with a verification code (6-8 digits)
   d. Extract the code
   e. Navigate back to X login page
   f. Enter the verification code
6. Wait until successfully logged in (URL contains '/home')
7. Use browser_evaluate to get the raw cookie string by running:
   () => document.cookie
8. Your FINAL response must be ONLY the exact string returned by browser_evaluate from step 7
   - NO explanations, NO error messages, NO additional text
   - ONLY the raw cookie string (format: "name1=value1; name2=value2; ...")
   - If you cannot get the cookies, use browser_evaluate anyway and return whatever document.cookie gives you

IMPORTANT:
- Use browser_snapshot before each interaction to see page state
- Adapt to actual page content, don't assume selectors
- Your final message must contain ONLY the cookie string, nothing else
- If any step fails 2 times in a row (like login submission), STOP and report the error
- Do NOT keep retrying failed actions - this could lock the account
- If you see console errors indicating bot detection or API failures, STOP immediately
"""

            # Validator that Claude will use to self-correct
            def validate_cookie_string(response: str) -> tuple[bool, str]:
                """Validate that response contains a valid cookie string."""
                response = response.strip()
                if not response:
                    return (
                        False,
                        "Response is empty. Must contain cookie string from document.cookie.",
                    )

                # Must not contain newlines (raw cookie string is single line)
                if "\n" in response:
                    return (
                        False,
                        "Invalid format. Response must be the RAW cookie string from browser_evaluate(() => document.cookie), not explanatory text. No newlines allowed.",
                    )

                # Must contain semicolon separator for multiple cookies
                if ";" not in response:
                    return (
                        False,
                        "Invalid cookie string. Must contain semicolon separators between cookies (name1=value1; name2=value2).",
                    )

                # Basic check: cookie string format is "name=value; name2=value2"
                if "=" not in response:
                    return (
                        False,
                        "Invalid cookie string format. Must contain at least one name=value pair.",
                    )

                return True, ""

            # Execute task via Claude agent with validation
            logger.info("Starting Claude agent task execution")
            result = await agent.execute_task(
                task=task,
                mcp_session=session,
                validator=validate_cookie_string,
            )

            # Prepare response
            if not result["success"]:
                logger.error(
                    f"[{request_id}] Task execution failed: {result.get('error')}"
                )
                response = CookieResponse(
                    success=False,
                    error=result.get("error", "Unknown error"),
                )
            else:
                # Extract cookie string from response
                cookie_string = result["response"].strip()
                logger.info(
                    f"[{request_id}] Successfully retrieved cookies (length: {len(cookie_string)})"
                )
                response = CookieResponse(
                    success=True,
                    cookies=cookie_string,
                    iterations=result.get("iterations"),
                )

            # Send webhook
            await send_webhook(webhook_url, response, request_id)

            return response

    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error during cookie retrieval")
        error_response = CookieResponse(success=False, error=str(e))

        # Send error webhook
        try:
            await send_webhook(webhook_url, error_response, request_id)
        except Exception as webhook_error:
            logger.error(
                f"[{request_id}] Failed to send error webhook: {webhook_error}"
            )

        return error_response


async def send_webhook(webhook_url: str, response: CookieResponse, request_id: str):
    """Send result to webhook URL."""
    payload = WebhookPayload(
        success=response.success,
        cookies=response.cookies,
        error=response.error,
        iterations=response.iterations,
        request_id=request_id,
    )

    try:
        logger.info(f"[{request_id}] Sending webhook to {webhook_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            webhook_response = await client.post(
                webhook_url, json=payload.model_dump(exclude_none=True)
            )
            webhook_response.raise_for_status()
            logger.info(
                f"[{request_id}] Webhook sent successfully. Status: {webhook_response.status_code}"
            )
    except Exception as e:
        logger.error(f"[{request_id}] Failed to send webhook: {e}")


@app.post("/get-cookies")
async def get_cookies(
    request: CookieRequest, background_tasks: BackgroundTasks
) -> TaskStatusResponse:
    """
    Authenticate with X using Claude + Playwright MCP.
    Returns immediately and sends results to webhook_url when complete.
    """
    request_id = str(uuid.uuid4())

    logger.info(f"[{request_id}] Received request for X username: {request.x_username}")

    background_tasks.add_task(
        process_cookie_request, request, request_id, str(request.webhook_url)
    )

    return TaskStatusResponse(
        status="processing",
        message="Task accepted. Results will be sent to webhook URL.",
        request_id=request_id,
    )
