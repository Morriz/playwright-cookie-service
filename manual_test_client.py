import asyncio
import os

import httpx

from logger import setup_logger

logger = setup_logger(__name__)


async def test_cookie_service():
    """
    Test webhook mode against the running playwright service.
    Sends request with webhook URL and returns immediately.

    Set credentials via environment variables:
    - X_USERNAME
    - X_EMAIL
    - X_PASSWORD
    - PROTONMAIL_EMAIL
    - PROTONMAIL_PASSWORD

    NOTE: Start webhook receiver first: python test_webhook_receiver.py
    """

    # Load credentials from environment
    x_username = os.getenv("X_USERNAME")
    x_email = os.getenv("X_EMAIL")
    x_password = os.getenv("X_PASSWORD")
    protonmail_email = os.getenv("PROTONMAIL_EMAIL")
    protonmail_password = os.getenv("PROTONMAIL_PASSWORD")

    if not all(
        [x_username, x_email, x_password, protonmail_email, protonmail_password]
    ):
        logger.error("❌ Missing required environment variables:")
        logger.error(
            "   X_USERNAME, X_EMAIL, X_PASSWORD, PROTONMAIL_EMAIL, PROTONMAIL_PASSWORD"
        )
        return False

    logger.info("🚀 Testing cookie service...")
    logger.info(f"   X Username: {x_username}")
    logger.info(f"   X Email: {x_email}")
    logger.info(f"   ProtonMail: {protonmail_email}")

    service_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Test 1: Health check
        try:
            logger.info("📡 Testing health endpoint...")
            response = await client.get(f"{service_url}/health")
            response.raise_for_status()
            logger.info(f"✅ Health check: {response.json()}")
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            logger.error("   Make sure service is running: docker-compose up")
            return False

        # Test 2: Request cookies with webhook
        logger.info("\n🔔 Requesting cookies with webhook callback...")

        try:
            response = await client.post(
                f"{service_url}/get-cookies",
                json={
                    "x_username": x_username,
                    "x_email": x_email,
                    "x_password": x_password,
                    "protonmail_email": protonmail_email,
                    "protonmail_password": protonmail_password,
                    "webhook_url": "http://host.docker.internal:9000/webhook",
                },
            )
            response.raise_for_status()
            result = response.json()

            # Should get immediate response
            if result.get("status") == "processing":
                logger.info("\n✅ Request accepted!")
                logger.info(f"   Request ID: {result.get('request_id')}")
                logger.info(f"   Status: {result.get('status')}")
                logger.info(f"   Message: {result.get('message')}")
                logger.info("\n⏳ Waiting for webhook callback...")
                logger.info("   (Check webhook receiver terminal for results)")
                return True

            # Fallback for sync response (shouldn't happen)
            if result.get("success") and result.get("cookies"):
                cookie_string = result["cookies"]

                # Parse cookie string: "name1=value1; name2=value2"
                cookies = {}
                for cookie in cookie_string.split("; "):
                    if "=" in cookie:
                        name, value = cookie.split("=", 1)
                        cookies[name] = value

                logger.info("\n✅ Cookie retrieval successful!")
                logger.info(f"   Retrieved {len(cookies)} cookies")
                logger.info(f"   Iterations: {result.get('iterations', 'N/A')}")
                logger.info("\n📋 Cookie names:")
                for key in cookies.keys():
                    logger.info(f"   - {key}")

                # Check for essential X cookies
                essential_cookies = ["auth_token", "ct0"]
                found_essential = [c for c in essential_cookies if c in cookies]
                if found_essential:
                    logger.info(f"\n✅ Found essential cookies: {found_essential}")
                else:
                    logger.warning(
                        f"\n⚠️  Warning: Essential cookies not found. Expected: {essential_cookies}"
                    )
                    logger.warning(f"   Available cookies: {list(cookies.keys())}")

                return True
            else:
                logger.error(f"\n❌ Cookie retrieval failed: {result.get('error')}")
                return False

        except httpx.HTTPError as e:
            logger.error(f"\n❌ HTTP error: {e}")
            if hasattr(e, "response"):
                logger.error(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"\n❌ Unexpected error: {e}")
            return False


async def main():
    logger.info("🔔 Testing webhook mode")
    logger.info("   Start webhook receiver first: python test_webhook_receiver.py\n")

    success = await test_cookie_service()
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
