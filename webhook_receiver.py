"""
Simple webhook receiver for testing webhook functionality.
Runs a local server on port 9000 to receive webhook callbacks.
"""

import asyncio

from fastapi import FastAPI, Request
from uvicorn import Config, Server

from logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="Webhook Test Receiver")


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receive and display webhook payload."""
    payload = await request.json()

    logger.info("=" * 80)
    logger.info("🎉 WEBHOOK RECEIVED!")
    logger.info("=" * 80)
    logger.info(f"Request ID: {payload.get('request_id')}")
    logger.info(f"Success: {payload.get('success')}")
    logger.info(f"Iterations: {payload.get('iterations', 'N/A')}")

    if payload.get("success"):
        cookies = payload.get("cookies", "")
        cookie_dict = {}
        for cookie in cookies.split("; "):
            if "=" in cookie:
                name, value = cookie.split("=", 1)
                cookie_dict[name] = value

        logger.info(f"Cookies ({len(cookie_dict)}): {list(cookie_dict.keys())}")
    else:
        logger.error(f"Error: {payload.get('error')}")

    logger.info("=" * 80)

    return {"status": "received"}


async def main():
    logger.info("🚀 Starting webhook receiver on http://localhost:9000")
    logger.info("   Webhook URL: http://localhost:9000/webhook")
    logger.info("\nPress Ctrl+C to stop\n")

    config = Config(app=app, host="0.0.0.0", port=9000, log_level="info")
    server = Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
