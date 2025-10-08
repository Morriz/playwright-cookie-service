import os
import uuid

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException

from claude_agent import ClaudePlaywrightAgent
from lib.auth import verify_apikey
from lib.logger import setup_logger
from mcp_client import MCPPlaywrightClient
from models import CookieRequest, CookieResponse, TaskStatusResponse, WebhookPayload
from services.browser_service import cleanup_login_traces, setup_browser_profile
from services.cookie_extractor import extract_cookies_from_trace
from services.task_builder import build_login_task

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

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not configured")
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        logger.info("Initializing Claude agent and MCP client")
        agent = ClaudePlaywrightAgent(api_key=anthropic_api_key)

        user_data_dir = setup_browser_profile()
        cleanup_login_traces(user_data_dir, request.login_url, request_id)

        mcp_client = MCPPlaywrightClient(user_data_dir=user_data_dir)

        logger.info(
            f"Connecting to Playwright MCP server with user data dir: {user_data_dir}"
        )
        async with mcp_client.connect() as session:
            task = build_login_task(request)
            logger.info("Starting Claude agent task execution")
            result = await agent.execute_task(task=task, mcp_session=session)

        logger.info(f"[{request_id}] Extracting cookies from trace file")

        if not result["success"]:
            e = f"Task execution failed: {result.get('error')}"
            logger.error(f"[{request_id}] {e}")
            raise Exception(e)

        cookie_string = extract_cookies_from_trace(
            user_data_dir, request.login_url, request_id
        )

        response = CookieResponse(
            success=True,
            cookies=cookie_string,
            iterations=result.get("iterations"),
        )

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
        async with httpx.AsyncClient(timeout=3) as client:
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
