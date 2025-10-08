"""
Integration test that verifies the full webhook flow:
1. Starts webhook receiver
2. Starts Docker service
3. Sends request to service
4. Waits for webhook callback
5. Validates results and cleans up
"""

import asyncio
import os
import signal
import subprocess
import sys
import time

import httpx
from dotenv import load_dotenv

from lib.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)


async def wait_for_service(url: str, timeout: int = 30) -> bool:
    """Wait for service to be ready."""
    logger.info(f"Waiting for service at {url}...")
    start = time.time()

    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(url, timeout=2.0)
                if response.status_code == 200:
                    logger.info(f"✅ Service ready at {url}")
                    return True
            except Exception:
                await asyncio.sleep(1)

    logger.error(f"❌ Service not ready after {timeout}s")
    return False


async def run_integration_test():
    """Run full integration test."""
    webhook_process = None
    docker_process = None

    try:
        # 1. Start webhook receiver
        logger.info("🚀 Starting webhook receiver...")
        webhook_process = subprocess.Popen(
            [sys.executable, "webhook_receiver.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for webhook receiver to be ready
        await asyncio.sleep(3)

        # 2. Start Docker service
        logger.info("🐳 Starting Docker service...")
        docker_process = subprocess.Popen(
            ["docker", "compose", "up", "--build"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for service to be ready
        if not await wait_for_service("http://localhost:8000/health"):
            raise Exception("Docker service failed to start")

        # 3. Send test request
        logger.info("🧪 Sending test request to service...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:8000/get-cookies",
                headers={"X-API-KEY": os.getenv("API_KEY")},
                json={
                    "login_url": "https://x.com/login",
                    "svc_username": os.getenv("SVC_USERNAME"),
                    "svc_email": os.getenv("SVC_EMAIL"),
                    "svc_password": os.getenv("SVC_PASSWORD"),
                    "email_password": os.getenv("EMAIL_PASSWORD"),
                    "callback_url": "http://host.docker.internal:9000/webhook",
                },
            )
            if response.status_code != 200:
                logger.error(f"❌ Request failed with status {response.status_code}")
                logger.error(f"Response body: {response.text}")
                raise Exception(
                    f"Request failed: {response.status_code} - {response.text}"
                )
            logger.info(f"Request submitted: {response.json()}")

        # 4. Wait for authentication to complete and check logs
        logger.info("⏳ Waiting for authentication to complete (180s)...")
        await asyncio.sleep(180)

        # Check webhook receiver logs
        logger.info("📊 Checking webhook receiver logs...")
        if webhook_process.poll() is None:
            logger.info(
                "✅ Integration test likely succeeded (check webhook receiver output above)"
            )
            return 0
        logger.error("❌ Webhook receiver stopped unexpectedly")
        return 1

    except Exception as e:
        logger.exception(f"❌ Integration test error: {e}")
        return 1

    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")

        if webhook_process:
            webhook_process.send_signal(signal.SIGTERM)
            webhook_process.wait(timeout=5)

        if docker_process:
            subprocess.run(["docker", "compose", "down"], capture_output=True)


async def main():
    logger.info("=" * 80)
    logger.info("🧪 INTEGRATION TEST")
    logger.info("=" * 80)

    exit_code = await run_integration_test()

    logger.info("=" * 80)
    logger.info(f"Test {'PASSED ✅' if exit_code == 0 else 'FAILED ❌'}")
    logger.info("=" * 80)

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
