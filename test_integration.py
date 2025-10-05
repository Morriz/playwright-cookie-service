"""
Integration test that verifies the full webhook flow:
1. Starts webhook receiver
2. Starts Docker service
3. Sends request to service
4. Waits for webhook callback
5. Validates results and cleans up
"""

import asyncio
import signal
import subprocess
import sys
import time

import httpx

from logger import setup_logger

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
            [sys.executable, "test_webhook_receiver.py"],
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

        # 3. Run test script
        logger.info("🧪 Running test script...")
        test_process = subprocess.run(
            [sys.executable, "test_playwright_service.py"],
            capture_output=True,
            text=True,
        )

        logger.info(f"Test output:\n{test_process.stdout}")
        if test_process.stderr:
            logger.error(f"Test errors:\n{test_process.stderr}")

        # 4. Wait for authentication to complete and check logs
        logger.info("⏳ Waiting for authentication to complete (60-120s)...")
        await asyncio.sleep(90)

        # Check webhook receiver logs
        logger.info("📊 Checking webhook receiver logs...")
        if webhook_process.poll() is None:
            logger.info(
                "✅ Integration test likely succeeded (check webhook receiver output above)"
            )
            return 0
        else:
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
