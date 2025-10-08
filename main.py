import glob
import json
import os
import shutil
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException

from claude_agent import ClaudePlaywrightAgent
from lib.auth import verify_apikey
from lib.logger import setup_logger
from mcp_client import MCPPlaywrightClient
from models import CookieRequest, CookieResponse, TaskStatusResponse, WebhookPayload

# Load environment variables from .env file
load_dotenv()

logger = setup_logger(__name__)

app = FastAPI(title="X Cookie Service")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


async def process_cookie_request(
    request: CookieRequest,
    request_id: str,
    callback_url: str,
):
    """
    Background task to process cookie retrieval and send webhook.
    """
    logger.info(
        f"[{request_id}] Processing cookie request for service username: {request.svc_username}"
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

        # Initialize MCP Playwright client with persistent user data dir
        # Use same dir every time so we can reuse cookies on subsequent runs
        user_data_dir = os.path.join(os.getcwd(), "browser_profile")
        os.makedirs(user_data_dir, exist_ok=True)

        # Clean up old traces before running
        traces_dir = os.path.join(user_data_dir, "traces")
        if os.path.exists(traces_dir):
            shutil.rmtree(traces_dir)
            logger.info(f"[{request_id}] Cleaned up old traces directory")

        mcp_client = MCPPlaywrightClient(user_data_dir=user_data_dir)

        # Connect to Playwright MCP and execute task
        logger.info(
            f"Connecting to Playwright MCP server with user data dir: {user_data_dir}"
        )
        async with mcp_client.connect() as session:
            # Construct task for Claude
            auth_type = (
                "username/password"
                if request.svc_username and request.svc_password
                else "magic link/email-only"
            )

            credentials_info = f"""
Credentials:
- Service Email: {request.svc_email}
- ProtonMail Email: {request.svc_email}
- ProtonMail Password: {request.email_password}
"""
            if request.svc_username:
                credentials_info += f"- Service Username: {request.svc_username}\n"
            if request.svc_password:
                credentials_info += f"- Service Password: {request.svc_password}\n"

            task = f"""
You are a browser automation expert. Your task is to log in to the authentication service.

Login URL: {request.login_url}
Authentication Type: {auth_type}

{credentials_info}

SECURITY - DO NOT ECHO CREDENTIALS:
- NEVER repeat passwords, usernames, emails, or verification codes in your responses
- NEVER log or output credential values
- Use generic descriptions like "entered the password" or "submitted verification code"
- Only reference credentials by type, never by value

Steps to follow:
1. Navigate to {request.login_url}
2. {"Enter the username and submit" if request.svc_username else "Enter the email if requested"}
3. If asked for email/phone verification, enter the email
4. {"Enter the password and submit" if request.svc_password else "Look for magic link or verification code sent to email"}
5. If a verification code or magic link is required:
   a. Open https://account.proton.me/login in a new tab or navigate to it
   b. Log in to ProtonMail with the provided credentials
   c. Find the latest email from the service with a verification code (6-8 digits) or magic link
   d. Extract the code or click the magic link
   e. Navigate back to the service login page if needed
   f. Enter the verification code if applicable
6. Wait until successfully logged in
7. Respond with "Login complete" when done

CRITICAL - ERROR REPORTING PROTOCOL:
If you encounter an unrecoverable error, respond with EXACTLY this format:
TASK_FAILED: <brief description of what went wrong>

Examples:
- TASK_FAILED: Bot detection blocked login with message "Could not log you in now"
- TASK_FAILED: Login failed after 2 attempts, password may be incorrect
- TASK_FAILED: Magic link not received after 2 minutes

IMPORTANT:
- Use browser_snapshot before each interaction to see page state
- Adapt to actual page content, don't assume selectors
- If any step fails 2 times in a row (like login submission), use TASK_FAILED protocol
- Do NOT keep retrying failed actions - this could lock the account
- If you see console errors indicating bot detection or API failures, use TASK_FAILED protocol immediately
- If the service shows error message "Could not log you in now. Please try again later.", use TASK_FAILED protocol IMMEDIATELY
"""

            # Execute task via Claude agent
            logger.info("Starting Claude agent task execution")
            result = await agent.execute_task(task=task, mcp_session=session)

        # MCP session closed - extract cookies from trace file
        logger.info(f"[{request_id}] Extracting cookies from trace file")

        if not result["success"]:
            e = f"Task execution failed: {result.get('error')}"
            logger.error(f"[{request_id}] {e}")
            raise Exception(e)
        # Find and parse the network trace file
        traces_dir = os.path.join(user_data_dir, "traces")
        trace_files = glob.glob(os.path.join(traces_dir, "*.network"))

        if not trace_files:
            e = "No trace files found"
            logger.error(f"[{request_id}] {e}")
            raise Exception(e)
        # Get the most recent trace file
        latest_trace = max(trace_files, key=os.path.getmtime)
        logger.info(f"[{request_id}] Reading trace file: {latest_trace}")

        # Parse JSONC (JSON Lines) - each line is a separate JSON object
        cookie_string = None
        all_cookies = {}  # Collect all unique cookies from X API calls
        api_calls_found = []
        sample_headers = None

        with open(latest_trace) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    snapshot = record.get("snapshot", {})
                    request_data = snapshot.get("request", {})
                    url = request_data.get("url", "")

                    # Look for any X/Twitter API calls (api.x.com or api.twitter.com)
                    if ("api.x.com" in url or "api.twitter.com" in url or "x.com" in url):
                        api_calls_found.append(url)
                        headers = request_data.get("headers", [])

                        # Capture first API call's headers for debugging
                        if sample_headers is None and headers:
                            sample_headers = headers

                        for header in headers:
                            header_name = header.get("name", "").lower()
                            if header_name == "cookie":
                                cookie_value = header.get("value", "")
                                if cookie_value:
                                    # Parse cookies and merge
                                    for cookie in cookie_value.split("; "):
                                        if "=" in cookie:
                                            name, value = cookie.split("=", 1)
                                            all_cookies[name] = value
                except json.JSONDecodeError:
                    continue

        logger.info(f"[{request_id}] Found {len(api_calls_found)} X/Twitter API calls in trace")
        logger.debug(f"[{request_id}] API calls: {api_calls_found[:5]}")  # Log first 5

        if sample_headers:
            header_names = [h.get("name", "") for h in sample_headers]
            logger.info(f"[{request_id}] Sample headers from first API call: {header_names}")
        else:
            logger.warning(f"[{request_id}] No headers found in API calls")

        if all_cookies:
            # Reconstruct cookie string from all collected cookies
            cookie_string = "; ".join([f"{name}={value}" for name, value in all_cookies.items()])
            logger.info(f"[{request_id}] Collected {len(all_cookies)} unique cookies")

        if not cookie_string:
            e = f"No cookies found in trace file. Found {len(api_calls_found)} API calls but no cookies."
            logger.error(f"[{request_id}] {e}")
            raise Exception(e)
        logger.info(f"[{request_id}] Successfully extracted cookies from trace")
        response = CookieResponse(
            success=True,
            cookies=cookie_string,
            iterations=result.get("iterations"),
        )

        # Send webhook
        await send_webhook(callback_url, response, request_id)

    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error during cookie retrieval")


async def send_webhook(callback_url: str, response: CookieResponse, request_id: str):
    """Send result to webhook URL."""
    payload = WebhookPayload(
        success=response.success,
        cookies=response.cookies,
        error=response.error,
        iterations=response.iterations,
        request_id=request_id,
    )

    try:
        logger.info(f"[{request_id}] Sending webhook to {callback_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            webhook_response = await client.post(
                callback_url, json=payload.model_dump(exclude_none=True)
            )
            webhook_response.raise_for_status()
            logger.info(
                f"[{request_id}] Webhook sent successfully. Status: {webhook_response.status_code}"
            )
    except Exception as e:
        logger.error(f"[{request_id}] Failed to send webhook: {e}")


@app.post("/get-cookies")
async def get_cookies(
    request: CookieRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(verify_apikey),
) -> TaskStatusResponse:
    """
    Authenticate with X using Claude + Playwright MCP.
    Returns immediately and sends results to callback_url when complete.
    """
    request_id = str(uuid.uuid4())

    logger.info(
        f"[{request_id}] Received request for service username: {request.svc_username}"
    )

    background_tasks.add_task(
        process_cookie_request, request, request_id, str(request.callback_url)
    )

    return TaskStatusResponse(
        request_id=request_id,
    )
